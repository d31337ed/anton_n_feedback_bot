import os
from telethon import TelegramClient
from telethon.tl import functions
from telethon.tl.types import PeerChannel, InputChannel

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
CHAT_PEER_ID = int(os.getenv("CHAT_PEER_ID"))

async def get_topic_title(topic_id: int):
    async with TelegramClient("session_name", API_ID, API_HASH) as client:
        peer = await client.get_input_entity(PeerChannel(CHAT_PEER_ID))
        chat_ref = InputChannel(channel_id=peer.channel_id,
                                access_hash=peer.access_hash)
        result = await client(functions.channels.GetForumTopicsByIDRequest(channel=chat_ref,
                                                                           topics=[topic_id]))
        return result.topics[0].title
