import logging
from aiogram import Router, Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from button_handlers import handlers
from keyboards import *
from settings import settings
from texts import t, text_key
from hotel_requests import mark_answered
from topic_registry import get_topic_user_id, release_topic_user

message_router = Router()

@message_router.message(F.forum_topic_closed)
async def topic_closed_handler(message: Message, bot: Bot) -> None:
    # Topics the bot closes itself (/close) are released by the command handler.
    if message.from_user.id == settings.bot_id:
        return
    logging.info(f"Forum topic {message.message_thread_id} closed by admin {message.from_user.id}")
    await release_topic_user(bot, message.message_thread_id)

@message_router.message()
async def input_handler(message: Message, state: FSMContext, bot: Bot, album: list[Message] | None = None) -> None:
    try:
        if message.message_thread_id is not None and message.from_user.id != settings.bot_id:
            # Service messages can't be copied to the user.
            if message.forum_topic_reopened or message.forum_topic_edited or message.pinned_message:
                return
            reply_to_chat_id = await get_topic_user_id(message.message_thread_id)
            if reply_to_chat_id is None:
                logging.warning(f"No user registered for forum topic {message.message_thread_id}")
                if message.message_thread_id != settings.error_topic_id:
                    await bot.send_message(text=f"No user registered for topic ID={message.message_thread_id}, message not delivered",
                                           chat_id=settings.chat_id, message_thread_id=settings.error_topic_id)
                return
            if album:
                await bot.copy_messages(chat_id=reply_to_chat_id, from_chat_id=settings.chat_id,
                                        message_ids=[m.message_id for m in album])
            else:
                await bot.copy_message(chat_id=reply_to_chat_id, from_chat_id=settings.chat_id, message_id=message.message_id)
            await mark_answered(bot, message.message_thread_id)
            return
        handler = handlers.get(text_key(message.text, "buttons."))
        if handler:
            logging.info(f"Button '{message.text}' pressed by user {message.from_user.id} in state {await state.get_state()}")
            await handler(message, state)
        elif message.from_user.id != settings.bot_id:
            await message.answer(text=t("common.no_input"), parse_mode="html")
    except Exception as e:
        error_text = f'Returned feedback error to user with ID={message.from_user.id}. Error: {e}'
        logging.error(error_text)
        await bot.send_message(text=error_text, chat_id=settings.chat_id, message_thread_id=settings.error_topic_id)
        await message.answer(text=t("common.error"), parse_mode='html')