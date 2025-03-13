import ecs_logging
import asyncio
import sys

import command_handlers
import message_handler
import state_handlers

import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from states import *
from keyboards import *

API_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
LOG_PATH = './logs/feedback_bot.log'
ERROR_TOPIC_ID = int(os.getenv("ERROR_TOPIC_ID"))
BOT_ID = int(API_TOKEN.split(":")[0])

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
dp.include_router(state_handlers.state_router)
dp.include_router(message_handler.message_router)


@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    try:
        await state.set_state(WelcomeFlow.start_state)
        user_id = str(message.from_user.id)
        user_name = message.from_user.first_name
        logging.info('Received feedback /start from ' + user_id)
        await message.answer(text=WELCOME_MESSAGE.format(user_name=user_name),
                         parse_mode="html",
                         reply_markup=MainMenuKeyboard)
    except Exception as e:
        error_text = 'Returned feedback error to user with ID=' + str(message.from_user.id) + '. Error: ' + str(e)
        logging.error(error_text)
        await bot.send_message(text=error_text,
                               chat_id=CHAT_ID,
                               message_thread_id=ERROR_TOPIC_ID)
        await message.answer(text=ERROR_TEXT, parse_mode='html')


@dp.message(Command("close"))
async def handle_close(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    if message.message_thread_id is not None:
        await bot.close_forum_topic(chat_id=CHAT_ID,
                                    message_thread_id=message.message_thread_id)
        user_state = FSMContext(storage=dp.storage,
                                key = StorageKey(chat_id=user_id, user_id=user_id, bot_id=BOT_ID))
        await user_state.clear()
    else:
        user_data = await state.get_data()
        user_active_topic_id = user_data["topic_id"]
        await bot.close_forum_topic(chat_id=CHAT_ID,
                                    message_thread_id=user_active_topic_id)
        await state.clear()
        await bot.send_message(chat_id=user_id, reply_markup=MainMenuKeyboard,
                               text=INQUIRY_CLOSED, disable_notification=True)


async def main() -> None:
    logging.info('Yay starting bot')
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    filebeat_handler = logging.FileHandler(LOG_PATH)
    filebeat_handler.setFormatter(ecs_logging.StdlibFormatter())
    logger = logging.getLogger()
    logger.addHandler(filebeat_handler)
    asyncio.run(main())
