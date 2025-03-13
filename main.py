import logging
import os
import ecs_logging
import asyncio
import sys
from aiogram import Bot, Dispatcher, types
import command_handlers
import state_handlers
from get_topic_title import get_topic_title
from button_handlers import *
from literals import *

API_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
LOG_PATH = './logs/feedback_bot.log'
ERROR_TOPIC_ID = int(os.getenv("ERROR_TOPIC_ID"))
BOT_ID = int(API_TOKEN.split(":")[0])

dp = Dispatcher()
bot = Bot(token=API_TOKEN)

dp.include_router(command_handlers.command_router)
dp.include_router(state_handlers.state_router)

@dp.message()
async def input_handler(message: Message, state: FSMContext) -> None:
    try:
        handler = handlers.get(message.text)
        if handler:
            await handler(message, state)
        elif message.message_thread_id is not None and message.from_user.id != BOT_ID:
            title = await get_topic_title(message.message_thread_id)
            reply_to_chat_id = title.split("[id=")[-1][:-1]
            await bot.copy_message(chat_id=reply_to_chat_id, from_chat_id=CHAT_ID, message_id=message.message_id)
        elif message.from_user.id != BOT_ID:
            await message.answer(text=NO_INPUT)
    except Exception as e:
        error_text = f'Returned feedback error to user with ID={message.from_user.id}. Error: {e}'
        logging.error(error_text)
        await bot.send_message(text=error_text, chat_id=CHAT_ID, message_thread_id=ERROR_TOPIC_ID)
        await message.answer(text=ERROR_TEXT, parse_mode='html')

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
