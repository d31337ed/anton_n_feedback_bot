import ecs_logging
import asyncio
import sys
import logging
import message_handler
import state_handlers
from os import getenv
from redis.asyncio import Redis as AioRedis
from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from states import *
from keyboards import *
from literals import *
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = getenv("BOT_TOKEN")
CHAT_ID = getenv("CHAT_ID")
LOG_PATH = './logs/feedback_bot.log'
ERROR_TOPIC_ID = int(getenv("ERROR_TOPIC_ID"))
BOT_ID = int(API_TOKEN.split(":")[0])
REDIS_HOST = getenv('REDIS_HOST')
REDIS_PORT = int(getenv('REDIS_PORT'))
REDIS_DB = int(getenv('REDIS_DB'))

storage = None
router = Router()
dp = Dispatcher()
bot = Bot(token=API_TOKEN)


async def main() -> None:
    global storage, dp
    redis = AioRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    storage = RedisStorage(redis)
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    dp.include_router(state_handlers.state_router)
    dp.include_router(message_handler.message_router)
    logging.info('Starting bot')
    await dp.start_polling(bot)

@router.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    try:
        user_id = str(message.from_user.id)
        user_name = message.from_user.first_name
        await state.set_state(WelcomeFlow.start_state)
        logging.info(f"Received feedback /start from user: {user_id}, Name: {user_name}")
        await message.answer(text=WELCOME_MESSAGE.format(user_name=user_name),
                             parse_mode="html",
                             reply_markup=MainMenuKeyboard)
        logging.info(f"Sent welcome message to user {user_id} with name {user_name}")
    except Exception as e:
        error_text = f"Returned feedback error to user with ID={str(message.from_user.id)}. Error: {str(e)}"
        logging.error(error_text)
        await bot.send_message(text=error_text,
                               chat_id=CHAT_ID,
                               message_thread_id=ERROR_TOPIC_ID)
        logging.info(f"Error sent to admin for user {message.from_user.id}")
        await message.answer(text=ERROR_TEXT, parse_mode='html')

@router.message(Command("close"))
async def handle_close(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logging.info(f"Received /close command from user {user_id}")
    await state.set_state(WelcomeFlow.start_state)
    if message.message_thread_id is not None:
        logging.info(f"Closing forum topic with ID: {message.message_thread_id}")
        await bot.close_forum_topic(chat_id=CHAT_ID,
                                    message_thread_id=message.message_thread_id)
        user_state = FSMContext(storage=dp.storage,
                                key=StorageKey(chat_id=user_id, user_id=user_id, bot_id=BOT_ID))
        await user_state.clear()
        logging.info(f"Cleared FSM state for user {user_id}")
    else:
        user_data = await state.get_data()
        try:
            user_active_topic_id = user_data["topic_id"]
            logging.info(f"Closing active forum topic with ID: {user_active_topic_id} for user {user_id}")
            await bot.close_forum_topic(chat_id=CHAT_ID,
                                        message_thread_id=user_active_topic_id)
            await state.clear()
            logging.info(f"Cleared FSM state for user {user_id}")
            await bot.send_message(chat_id=user_id, reply_markup=MainMenuKeyboard,
                                   text=INQUIRY_CLOSED, parse_mode="html", disable_notification=True)
            logging.info(f"Sent inquiry closed message to user {user_id}")
        except KeyError:
            await message.reply(text=NO_TOPIC_TO_CLOSE, parse_mode="html", reply_markup=MainMenuKeyboard)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    filebeat_handler = logging.FileHandler(LOG_PATH)
    filebeat_handler.setFormatter(ecs_logging.StdlibFormatter())
    logger = logging.getLogger()
    logger.addHandler(filebeat_handler)
    asyncio.run(main())
