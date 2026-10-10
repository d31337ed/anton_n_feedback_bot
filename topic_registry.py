import html
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import User
from redis.asyncio import Redis

from keyboards import MainMenuKeyboard
from literals import INQUIRY_CLOSED, USER_CARD, USER_CARD_NO_USERNAME, USER_CARD_PROFILE_LINK_TEXT
from settings import settings

# Shared client and FSM storage: main.py hands the same storage to the dispatcher.
redis = Redis(host=settings.redis_host, port=settings.redis_port, db=settings.redis_db)
storage = RedisStorage(redis)


def topic_key(topic_id: int) -> str:
    return f"topic:{topic_id}"


def user_card(user: User) -> str:
    profile_url = f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
    return USER_CARD.format(full_name=html.escape(user.full_name),
                            username=f"@{user.username}" if user.username else USER_CARD_NO_USERNAME,
                            profile_link=f'<a href="{profile_url}">{USER_CARD_PROFILE_LINK_TEXT}</a>',
                            user_id=user.id)


async def create_topic(bot: Bot, name: str, user: User) -> int:
    forum_topic = await bot.create_forum_topic(chat_id=settings.chat_id, name=name)
    topic_id = forum_topic.message_thread_id
    await redis.set(topic_key(topic_id), str(user.id))
    logging.info(f"Registered forum topic {topic_id} for user {user.id}")
    # The card goes first, before any forwarded user message.
    await bot.send_message(chat_id=settings.chat_id, message_thread_id=topic_id, text=user_card(user), parse_mode="html")
    return topic_id


async def get_topic_user_id(topic_id: int) -> str | None:
    user_id = await redis.get(topic_key(topic_id))
    return user_id.decode() if user_id is not None else None


async def close_topic(bot: Bot, topic_id: int) -> None:
    # A topic already closed or deleted by an admin is not an error for /close.
    try:
        await bot.close_forum_topic(chat_id=settings.chat_id, message_thread_id=topic_id)
    except TelegramBadRequest as e:
        if "TOPIC_NOT_MODIFIED" in e.message:
            logging.info(f"Forum topic {topic_id} is already closed")
        elif "TOPIC_ID_INVALID" in e.message:
            logging.warning(f"Forum topic {topic_id} no longer exists")
        else:
            raise


async def show_main_menu_silently(bot: Bot, user_id: int) -> None:
    # A reply keyboard can only arrive with a message, and clients drop it once that message is deleted,
    # so the message stays - just without a notification sound.
    try:
        await bot.send_message(chat_id=user_id, text=INQUIRY_CLOSED, reply_markup=MainMenuKeyboard,
                               parse_mode="html", disable_notification=True)
        logging.info(f"Silently restored main menu for user {user_id}")
    except TelegramForbiddenError:
        logging.warning(f"User {user_id} blocked the bot, main menu not restored")


async def release_topic_user(bot: Bot, topic_id: int) -> None:
    # Called when an admin closes a topic: free the user from it and bring back the main menu.
    user_id = await get_topic_user_id(topic_id)
    if user_id is None:
        logging.warning(f"No user registered for forum topic {topic_id}, FSM state left as is")
        return
    user_id = int(user_id)
    user_state = FSMContext(storage=storage, key=StorageKey(chat_id=user_id, user_id=user_id, bot_id=settings.bot_id))
    # The user may already have another active topic - only drop state bound to this one.
    if (await user_state.get_data()).get("topic_id") != topic_id:
        return
    await user_state.clear()
    logging.info(f"Cleared FSM state for user {user_id}")
    await show_main_menu_silently(bot, user_id)
