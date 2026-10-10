# One-off migration: build the topic -> user_id index in Redis from forum topic titles.
# Needs Telethon, so run it inside the pre-migration image, in the bot's working dir:
#   docker exec -i -w /anton_n_feedback_bot <container> python - [--dry-run] < migrate_topics.py
# Idempotent: existing keys are never overwritten (SET NX).
import asyncio
import json
import re
import shutil
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict
from redis.asyncio import Redis
from telethon import TelegramClient
from telethon.tl import functions
from telethon.tl.types import InputChannel, PeerChannel

TITLE_USER_ID = re.compile(r"\[id=(\d+)\]\s*$")
GENERAL_TOPIC_ID = 1


class MigrationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", secrets_dir="/run/secrets")

    error_topic_id: int
    redis_host: str
    redis_port: int = 6379
    redis_db: int = 0
    api_id: int
    api_hash: str
    chat_peer_id: int


async def fetch_topics(client, chat_peer_id):
    peer = await client.get_input_entity(PeerChannel(chat_peer_id))
    channel = InputChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
    topics = {}
    offset_date, offset_id, offset_topic = 0, 0, 0
    while True:
        res = await client(functions.channels.GetForumTopicsRequest(
            channel=channel, offset_date=offset_date, offset_id=offset_id,
            offset_topic=offset_topic, limit=100))
        batch = [t for t in res.topics if hasattr(t, "title")]
        new = [t for t in batch if t.id not in topics]
        # Pinned topics are repeated on every page, so stop once a page adds nothing.
        if not new:
            break
        topics.update({t.id: t for t in batch})
        last = batch[-1]
        messages = {m.id: m for m in res.messages}
        offset_topic = last.id
        offset_id = last.top_message
        offset_date = int(messages[last.top_message].date.timestamp()) if last.top_message in messages else 0
    return list(topics.values()), res.count


async def fsm_topic_users(redis):
    result = {}
    async for key in redis.scan_iter(match="fsm:*:data"):
        try:
            data = json.loads(await redis.get(key))
        except (TypeError, ValueError):
            continue
        if isinstance(data, dict) and "topic_id" in data:
            result[int(data["topic_id"])] = key.decode().split(":")[-2]
    return result


async def main(dry_run: bool):
    settings = MigrationSettings()
    # Work on a copy so the running bot keeps exclusive use of its session file.
    shutil.copy("session_name.session", "/tmp/migrate_topics.session")
    async with TelegramClient("/tmp/migrate_topics", settings.api_id, settings.api_hash) as client:
        topics, total = await fetch_topics(client, settings.chat_peer_id)
    print(f"Telegram reports {total} topics, fetched {len(topics)} unique")

    redis = Redis(host=settings.redis_host, port=settings.redis_port, db=settings.redis_db)
    fsm = await fsm_topic_users(redis)
    stats = {"written": 0, "already_present": 0, "conflict": 0, "skipped_service": 0, "unparsed": 0, "fsm_mismatch": 0}

    for topic in sorted(topics, key=lambda t: t.id):
        if topic.id in (GENERAL_TOPIC_ID, settings.error_topic_id):
            stats["skipped_service"] += 1
            continue
        match = TITLE_USER_ID.search(topic.title)
        if not match:
            stats["unparsed"] += 1
            print(f"UNPARSED topic={topic.id} closed={topic.closed} title={topic.title!r}")
            continue
        user_id = match.group(1)
        if topic.id in fsm and fsm[topic.id] != user_id:
            stats["fsm_mismatch"] += 1
            print(f"FSM MISMATCH topic={topic.id} title_user={user_id} fsm_user={fsm[topic.id]}")

        key = f"topic:{topic.id}"
        existing = await redis.get(key)
        if existing is not None:
            if existing.decode() == user_id:
                stats["already_present"] += 1
            else:
                stats["conflict"] += 1
                print(f"CONFLICT topic={topic.id} redis_user={existing.decode()} title_user={user_id}")
            continue
        if not dry_run:
            await redis.set(key, user_id, nx=True)
        stats["written"] += 1

    known = {t.id for t in topics}
    for topic_id, user_id in sorted(fsm.items()):
        if topic_id not in known:
            print(f"FSM topic missing in Telegram: topic={topic_id} user={user_id}")

    await redis.aclose()
    print(("DRY RUN, nothing written. " if dry_run else "") + str(stats))


if __name__ == "__main__":
    asyncio.run(main(dry_run="--dry-run" in sys.argv[1:]))
