import logging
from os import getenv
from telethon import TelegramClient
from telethon.tl import functions
from telethon.tl.types import PeerChannel, InputChannel

API_ID = int(getenv("API_ID"))
API_HASH = getenv("API_HASH")
CHAT_PEER_ID = int(getenv("CHAT_PEER_ID"))

async def get_topic_title(topic_id: int):
    logging.info(f"Attempting to retrieve topic title for topic ID: {topic_id}")
    async with TelegramClient("session_name", API_ID, API_HASH) as client:
        peer = await client.get_input_entity(PeerChannel(CHAT_PEER_ID))
        chat_ref = InputChannel(channel_id=peer.channel_id,
                                access_hash=peer.access_hash)
        logging.info(f"Got input entity for chat: {CHAT_PEER_ID}, channel ID: {peer.channel_id}")
        result = await client(functions.channels.GetForumTopicsByIDRequest(channel=chat_ref,
                                                                           topics=[topic_id]))
        logging.info(f"Successfully retrieved topic title: {result.topics[0].title} for topic ID: {topic_id}")
        return result.topics[0].title
