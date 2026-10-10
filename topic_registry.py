import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from redis.asyncio import Redis

from settings import settings

# Shared client: also backs the FSM storage in main.py.
redis = Redis(host=settings.redis_host, port=settings.redis_port, db=settings.redis_db)


def topic_key(topic_id: int) -> str:
    return f"topic:{topic_id}"


async def create_topic(bot: Bot, name: str, user_id: str) -> int:
    forum_topic = await bot.create_forum_topic(chat_id=settings.chat_id, name=name)
    topic_id = forum_topic.message_thread_id
    await redis.set(topic_key(topic_id), user_id)
    logging.info(f"Registered forum topic {topic_id} for user {user_id}")
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
