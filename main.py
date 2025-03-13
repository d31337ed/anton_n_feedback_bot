import logging
import os
import ecs_logging
import asyncio
import sys

from aiogram.filters import CommandStart
from aiogram import Bot, Dispatcher, types
from get_topic_title import get_topic_title
from button_handlers import *
from literals import *

API_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
LOG_PATH = './logs/feedback_bot.log'
ERROR_TOPIC_ID = 27
BOT_ID = int(API_TOKEN.split(":")[0])

dp = Dispatcher()
bot = Bot(token=API_TOKEN)

@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
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


@dp.message(AdvFlow.adv_in_offer_state)
async def process_public_question(message: types.Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name=IN_ADV_TOPIC.format(user_name=user_name,
                                                                        user_id=user_id))
    await message.forward(chat_id=CHAT_ID,
                          message_thread_id=forum_topic.message_thread_id)
    await message.reply(text=ADV_OFFER_RECEIVED_TEXT,
                        reply_markup=MainMenuKeyboard)
    await state.clear()

@dp.message(ServicesFlow.services_hotel_input_state)
async def process_hotel_request(message: types.Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name=HOTEL_REQUEST_TOPIC.format(user_name=user_name,
                                                                               user_id=user_id))
    await message.forward(chat_id=CHAT_ID,
                          message_thread_id=forum_topic.message_thread_id)
    await message.reply(text=ADV_OFFER_RECEIVED_TEXT,
                        reply_markup=MainMenuKeyboard)
    await state.clear()

@dp.message(AdvFlow.adv_in_special_offer_state)
async def process_public_question(message: types.Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name=IN_SPECIAL_TOPIC.format(user_name=user_name,
                                                                            user_id=user_id))
    await message.forward(chat_id=CHAT_ID, message_thread_id=forum_topic.message_thread_id)
    await message.reply(text=ADV_OFFER_RECEIVED_TEXT, reply_markup=MainMenuKeyboard)
    await state.clear()


@dp.message(QuestionFlow.public_question)
async def process_public_question(message: types.Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID, name=PUBLIC_QUESTION_TOPIC.format(user_name=user_name,
                                                                                                  user_id=user_id))
    await message.forward(chat_id=CHAT_ID, message_thread_id=forum_topic.message_thread_id)
    await message.reply(text=INQUIRY_SENT_TEXT, reply_markup=MainMenuKeyboard)
    await state.clear()


@dp.message(WelcomeFlow.other_inquiries_state)
async def process_public_question(message: types.Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name=OTHERS_TOPIC.format(user_name=user_name,
                                                                        user_id=user_id))
    await message.forward(chat_id=CHAT_ID, message_thread_id=forum_topic.message_thread_id)
    await message.reply(text=INQUIRY_SENT_TEXT, reply_markup=MainMenuKeyboard)
    await state.clear()

@dp.message(ReportIssueFlow.report_bot_problem)
async def process_public_question(message: types.Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name=ISSUE_BOT_TOPIC.format(user_name=user_name,
                                                                           user_id=user_id))
    await message.forward(chat_id=CHAT_ID, message_thread_id=forum_topic.message_thread_id)
    await message.reply(text=INQUIRY_SENT_TEXT, reply_markup=MainMenuKeyboard)
    await state.clear()

@dp.message(ReportIssueFlow.report_routes_problem)
async def process_public_question(message: types.Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name=ISSUE_ROUTES_TOPIC.format(user_name=user_name,
                                                                              user_id=user_id))
    await message.forward(chat_id=CHAT_ID, message_thread_id=forum_topic.message_thread_id)
    await message.reply(text=INQUIRY_SENT_TEXT, reply_markup=MainMenuKeyboard)
    await state.clear()

@dp.message(ReportIssueFlow.report_typo_problem)
async def process_public_question(message: types.Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name=ISSUE_TYPO_TOPIC.format(user_name=user_name, user_id=user_id))
    await message.forward(chat_id=CHAT_ID, message_thread_id=forum_topic.message_thread_id)
    await message.reply(text=INQUIRY_SENT_TEXT, reply_markup=MainMenuKeyboard)
    await state.clear()

@dp.message()
async def input_handler(message: Message, state: FSMContext) -> None:
    try:
        handler = handlers.get(message.text)
        if handler:
            await handler(message, state)
        elif message.message_thread_id is not None and message.from_user.id != BOT_ID:
            title = await get_topic_title(message.message_thread_id)
            reply_to_chat_id = title.split("[id=")[-1][:-1]
            await bot.send_message(chat_id=reply_to_chat_id, text=message.text)
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
