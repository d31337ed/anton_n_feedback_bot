import logging
from aiogram import Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from button_handlers import handlers
from get_topic_title import get_topic_title
from keyboards import *
from settings import settings

message_router = Router()

@message_router.message()
async def input_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    try:
        handler = handlers.get(message.text)
        if handler:
            await handler(message, state)
        elif message.message_thread_id is not None and message.from_user.id != settings.bot_id:
            title = await get_topic_title(message.message_thread_id)
            reply_to_chat_id = title.split("[id=")[-1][:-1]
            await bot.copy_message(chat_id=reply_to_chat_id, from_chat_id=settings.chat_id, message_id=message.message_id)
        elif message.from_user.id != settings.bot_id:
            await message.answer(text=NO_INPUT, parse_mode="html")
    except Exception as e:
        error_text = f'Returned feedback error to user with ID={message.from_user.id}. Error: {e}'
        logging.error(error_text)
        await bot.send_message(text=error_text, chat_id=settings.chat_id, message_thread_id=settings.error_topic_id)
        await message.answer(text=ERROR_TEXT, parse_mode='html')