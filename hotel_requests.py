import html
import json
import logging
import time
from datetime import date, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import User

from keyboards import hotel_edit_keyboard
from literals import *
from settings import settings
from states import ServicesFlow
from topic_registry import create_topic, redis, storage

# A request is bound to its forum topic: one open hotel branch = one topic = one request.
NEW, ACCEPTED, IN_WORK, CLOSED = "new", "accepted", "in_work", "closed"

MODE_HOTEL, MODE_CITY = "hotel", "city"
MODE_LABELS = {MODE_HOTEL: "Конкретный отель", MODE_CITY: "Подбор в городе"}
ROOM_TYPES = ("Стандартный", "Делюкс", "Люкс")
# Summary order; fields of the inactive mode are dropped on submit.
FIELD_LABELS = {
    "mode": "Режим",
    "hotel": "Отель",
    "city": "Город",
    "price_cap": "Потолок цены за ночь",
    "check_in": "Заезд",
    "check_out": "Выезд",
    "adults": "Взрослые",
    "children": "Дети",
    "room_type": "Тип номера",
    "comment": "Комментарий",
}
MODE_FIELDS = {MODE_HOTEL: {"hotel"}, MODE_CITY: {"city", "price_cap"}}
MAX_TEXT, MAX_COMMENT, MAX_GUESTS, MAX_NIGHTS, MAX_PRICE = 200, 2000, 20, 90, 1_000_000


class ValidationError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__(errors)
        self.errors = errors


def request_key(topic_id: int) -> str:
    return f"request:{topic_id}"


def answered_key(topic_id: int) -> str:
    return f"topic:{topic_id}:answered"


def _text(raw: dict, name: str, limit: int, errors: dict, required: bool) -> str | None:
    value = str(raw.get(name) or "").strip()
    if not value:
        if required:
            errors[name] = "Обязательное поле"
        return None
    if len(value) > limit:
        errors[name] = f"Не больше {limit} символов"
    return value


def _int(raw: dict, name: str, low: int, high: int, errors: dict, default: int | None = None) -> int | None:
    value = raw.get(name)
    if value in (None, ""):
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        errors[name] = "Нужно целое число"
        return None
    if not low <= number <= high:
        errors[name] = f"От {low} до {high}"
    return number


def _date(raw: dict, name: str, errors: dict) -> date | None:
    try:
        return date.fromisoformat(str(raw.get(name) or ""))
    except ValueError:
        errors[name] = "Укажите дату"
        return None


def clean_fields(raw: dict) -> dict:
    """Validates the submitted form and returns only the fields of the selected mode."""
    errors: dict[str, str] = {}
    mode = raw.get("mode")
    if mode not in MODE_LABELS:
        raise ValidationError({"mode": "Выберите режим"})
    fields = {"mode": mode}
    if mode == MODE_HOTEL:
        fields["hotel"] = _text(raw, "hotel", MAX_TEXT, errors, required=True)
    else:
        fields["city"] = _text(raw, "city", MAX_TEXT, errors, required=True)
        fields["price_cap"] = _int(raw, "price_cap", 1, MAX_PRICE, errors)
    check_in, check_out = _date(raw, "check_in", errors), _date(raw, "check_out", errors)
    # One day of slack: the client's "today" may already be tomorrow in UTC terms.
    if check_in and check_in < date.today() - timedelta(days=1):
        errors["check_in"] = "Дата заезда уже прошла"
    if check_in and check_out:
        if check_out <= check_in:
            errors["check_out"] = "Выезд должен быть позже заезда"
        elif (check_out - check_in).days > MAX_NIGHTS:
            errors["check_out"] = f"Не больше {MAX_NIGHTS} ночей"
    fields["check_in"] = check_in.isoformat() if check_in else None
    fields["check_out"] = check_out.isoformat() if check_out else None
    fields["adults"] = _int(raw, "adults", 1, MAX_GUESTS, errors, default=2)
    fields["children"] = _int(raw, "children", 0, MAX_GUESTS, errors, default=0)
    room_type = raw.get("room_type") or ROOM_TYPES[0]
    if room_type not in ROOM_TYPES:
        errors["room_type"] = "Выберите тип номера"
    fields["room_type"] = room_type
    fields["comment"] = _text(raw, "comment", MAX_COMMENT, errors, required=False)
    if errors:
        raise ValidationError(errors)
    # No children is the default and is left out of the summary like any empty optional field.
    return {name: value for name, value in fields.items() if value is not None and (name, value) != ("children", 0)}


def _plural(number: int, one: str, few: str, many: str) -> str:
    if number % 10 == 1 and number % 100 != 11:
        return one
    if 2 <= number % 10 <= 4 and not 12 <= number % 100 <= 14:
        return few
    return many


def format_value(fields: dict, name: str) -> str:
    value = fields[name]
    if name == "mode":
        return MODE_LABELS[value]
    if name == "check_in":
        return date.fromisoformat(value).strftime("%d.%m.%Y")
    if name == "check_out":
        nights = (date.fromisoformat(value) - date.fromisoformat(fields["check_in"])).days
        return f"{date.fromisoformat(value).strftime('%d.%m.%Y')} ({nights} {_plural(nights, 'ночь', 'ночи', 'ночей')})"
    if name == "price_cap":
        return f"до ${value}"
    return html.escape(str(value))


def format_fields(fields: dict) -> str:
    return "\n".join(f"<b>{label}</b>: {format_value(fields, name)}"
                     for name, label in FIELD_LABELS.items() if name in fields)


def format_changes(old: dict, new: dict) -> str:
    lines = []
    for name, label in FIELD_LABELS.items():
        before = format_value(old, name) if name in old else "—"
        after = format_value(new, name) if name in new else "—"
        if before != after:
            lines.append(f"<b>{label}</b>: {before} → {after}")
    return "\n".join(lines)


async def get_request(topic_id: int) -> dict | None:
    raw = await redis.get(request_key(topic_id))
    return json.loads(raw) if raw else None


async def save_request(record: dict) -> None:
    await redis.set(request_key(record["topic_id"]), json.dumps(record, ensure_ascii=False))


def user_state(user_id: int) -> FSMContext:
    return FSMContext(storage=storage, key=StorageKey(chat_id=user_id, user_id=user_id, bot_id=settings.bot_id))


async def resolve(user_id: int, request_id: int | None) -> tuple[str, int | None, dict | None]:
    """Returns (status, topic_id, record) of the request the form is opened for.

    Raises LookupError when request_id points to someone else's or an unknown request.
    """
    state = user_state(user_id)
    current_state, data = await state.get_state(), await state.get_data()
    active_topic = data.get("topic_id") if current_state == ServicesFlow.services_book_hotel_state.state else None
    if request_id is not None:
        record = await get_request(request_id)
        if record is None or record["user_id"] != user_id:
            raise LookupError(request_id)
        topic_id = request_id
        # /close and admin closing both clear the FSM binding, so a mismatch means the request is closed.
        if active_topic != topic_id:
            return CLOSED, topic_id, record
    elif active_topic is not None:
        topic_id, record = active_topic, await get_request(active_topic)
    elif current_state == ServicesFlow.services_book_hotel_state.state:
        return NEW, None, None
    else:
        # Opened from an entry message of a branch the user has already left.
        return CLOSED, None, None
    if await redis.exists(answered_key(topic_id)):
        return IN_WORK, topic_id, record
    return ACCEPTED, topic_id, record


def _telegram_user(user) -> User:
    return User(id=user.id, is_bot=False, first_name=user.first_name, last_name=user.last_name,
                username=user.username)


async def submit(bot: Bot, user, fields: dict, request_id: int | None) -> tuple[str, int | None]:
    """Creates or updates the request. Returns (status, topic_id); only ACCEPTED means it was saved."""
    status, topic_id, record = await resolve(user.id, request_id)
    if status in (IN_WORK, CLOSED):
        return status, topic_id
    now = int(time.time())
    if status == NEW:
        tg_user = _telegram_user(user)
        topic_id = await create_topic(bot, user=tg_user,
                                      name=HOTEL_REQUEST_TOPIC.format(user_name=tg_user.full_name, user_id=user.id))
        await user_state(user.id).set_data({"topic_id": topic_id})
        logging.info(f"Created hotel request topic {topic_id} for user {user.id} from the form")
        await bot.send_message(chat_id=settings.chat_id, message_thread_id=topic_id, parse_mode="html",
                               text=HOTEL_FORM_TOPIC_NEW.format(fields=format_fields(fields)))
        record = {"topic_id": topic_id, "user_id": user.id, "created_at": now}
    elif record is None or "fields" not in record:
        # The request was opened by a text message; the form completes it.
        await bot.send_message(chat_id=settings.chat_id, message_thread_id=topic_id, parse_mode="html",
                               text=HOTEL_FORM_TOPIC_FILLED.format(fields=format_fields(fields)))
        record = {"topic_id": topic_id, "user_id": user.id, "created_at": now}
    else:
        changes = format_changes(record["fields"], fields)
        await bot.send_message(chat_id=settings.chat_id, message_thread_id=topic_id, parse_mode="html",
                               text=HOTEL_FORM_TOPIC_EDITED.format(changes=changes) if changes
                               else HOTEL_FORM_TOPIC_UNCHANGED)
    updated = "summary_message_id" in record
    record.update(fields=fields, updated_at=now)
    summary = HOTEL_FORM_SUMMARY.format(fields=format_fields(fields),
                                        updated=HOTEL_FORM_SUMMARY_UPDATED if updated else "")
    keyboard = hotel_edit_keyboard(topic_id)
    if updated:
        try:
            await bot.edit_message_text(chat_id=user.id, message_id=record["summary_message_id"], text=summary,
                                        parse_mode="html", reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in e.message:
                raise
    else:
        message = await bot.send_message(chat_id=user.id, text=summary, parse_mode="html", reply_markup=keyboard)
        record["summary_message_id"] = message.message_id
    await save_request(record)
    logging.info(f"Saved hotel request {topic_id} for user {user.id} ({'updated' if updated else 'new summary'})")
    return ACCEPTED, topic_id


async def mark_answered(bot: Bot, topic_id: int) -> None:
    """Called on every admin message in a topic; the first one closes editing via the form."""
    if not await redis.set(answered_key(topic_id), 1, nx=True):
        return
    record = await get_request(topic_id)
    if not record or "summary_message_id" not in record:
        return
    try:
        await bot.edit_message_reply_markup(chat_id=record["user_id"], message_id=record["summary_message_id"],
                                            reply_markup=None)
        logging.info(f"Removed edit button from hotel request {topic_id}")
    except TelegramBadRequest as e:
        logging.warning(f"Could not remove edit button from hotel request {topic_id}: {e.message}")
