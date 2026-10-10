import html
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import User
from redis.asyncio import Redis

from literals import USER_CARD, USER_CARD_NO_USERNAME, USER_CARD_PROFILE_LINK_TEXT
from settings import settings

# Shared client: also backs the FSM storage in main.py.
redis = Redis(host=settings.redis_host, port=settings.redis_port, db=settings.redis_db)


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
