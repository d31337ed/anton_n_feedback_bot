import json
import logging
import time

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import User

import hotel_form
from keyboards import hotel_edit_keyboard
from literals import *
from settings import settings
from states import ServicesFlow
from topic_registry import create_topic, redis, storage

# A request is bound to its forum topic: one open hotel branch = one topic = one request.
NEW, ACCEPTED, IN_WORK, CLOSED = "new", "accepted", "in_work", "closed"



def request_key(topic_id: int) -> str:
    return f"request:{topic_id}"


def answered_key(topic_id: int) -> str:
    return f"topic:{topic_id}:answered"


def preferences_key(user_id: int) -> str:
    return f"hotel_prefs:{user_id}"


async def get_request(topic_id: int) -> dict | None:
    raw = await redis.get(request_key(topic_id))
    return json.loads(raw) if raw else None


async def save_request(record: dict) -> None:
    await redis.set(request_key(record["topic_id"]), json.dumps(record, ensure_ascii=False))


async def get_preferences(user_id: int) -> dict:
    raw = await redis.get(preferences_key(user_id))
    return hotel_form.clean_preferences(json.loads(raw)) if raw else {}


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


async def submit(bot: Bot, user, form: dict, request_id: int | None) -> tuple[str, int | None]:
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
                               text=HOTEL_FORM_TOPIC_NEW.format(fields=hotel_form.format_request(form)))
        record = {"topic_id": topic_id, "user_id": user.id, "created_at": now}
    elif record is None or "form" not in record:
        # The request was opened by a text message; the form completes it.
        await bot.send_message(chat_id=settings.chat_id, message_thread_id=topic_id, parse_mode="html",
                               text=HOTEL_FORM_TOPIC_FILLED.format(fields=hotel_form.format_request(form)))
        record = {"topic_id": topic_id, "user_id": user.id, "created_at": now}
    else:
        changes = hotel_form.format_changes(record["form"], form)
        await bot.send_message(chat_id=settings.chat_id, message_thread_id=topic_id, parse_mode="html",
                               text=HOTEL_FORM_TOPIC_EDITED.format(changes=changes) if changes
                               else HOTEL_FORM_TOPIC_UNCHANGED)
    updated = "summary_message_id" in record
    record.update(form=form, updated_at=now)
    summary = HOTEL_FORM_SUMMARY.format(fields=hotel_form.format_request(form),
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
    await redis.set(preferences_key(user.id), json.dumps(hotel_form.preferences_of(form)))
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
