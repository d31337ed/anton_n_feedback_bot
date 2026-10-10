import asyncio
import logging

from aiogram import BaseMiddleware
from aiogram.types import Message

# Quiet period after the last album part before the album is considered complete.
ALBUM_LATENCY = 1.0


class AlbumMiddleware(BaseMiddleware):
    """Collects the parts of a media group and runs the handler once, with all parts in data["album"]."""

    def __init__(self, latency: float = ALBUM_LATENCY):
        self.latency = latency
        self.albums: dict[tuple[int, str], list[Message]] = {}

    async def __call__(self, handler, event: Message, data: dict):
        if not event.media_group_id:
            return await handler(event, data)
        key = (event.chat.id, event.media_group_id)
        if key in self.albums:
            # Updates are processed concurrently: the first part's call is already waiting for the rest.
            self.albums[key].append(event)
            return
        self.albums[key] = [event]
        while True:
            parts = len(self.albums[key])
            await asyncio.sleep(self.latency)
            if len(self.albums[key]) == parts:
                break
        album = sorted(self.albums.pop(key), key=lambda m: m.message_id)
        logging.info(f"Collected album {event.media_group_id} of {len(album)} messages from chat {event.chat.id}")
        data["album"] = album
        return await handler(album[0], data)
