import logging
import os
import ecs_logging
import asyncio
import sys

from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from telethon import TelegramClient
from telethon.tl import functions
from telethon.tl.types import InputChannel
from literals import *

API_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
CHAT_ID = os.getenv("CHAT_ID")
CHAT_PEER_ID = os.getenv("CHAT_PEER_ID")
LOG_PATH = './logs/feedback_bot.log'
ERROR_TOPIC_ID = 27
BOT_ID = int(API_TOKEN.split(":")[0])

# Configure logging
logging.basicConfig(level=logging.INFO)
dp = Dispatcher()
bot = Bot(token=API_TOKEN)


class WelcomeFlow(StatesGroup):
    start_state = State()
    adv_state = State()
    services_state = State()
    questions_state = State()
    report_issue_state = State()
    other_inquiries_state = State()


class AdvFlow(StatesGroup):
    adv_out_offer_state = State()
    adv_in_offer_state = State()
    adv_in_special_offer_state = State()


class ServicesFlow(StatesGroup):
    services_book_hotel_state = State()
    services_order_status_match_state = State()
    services_order_lounge = State()


class QuestionFlow(StatesGroup):
    public_question = State()
    private_question = State()


class ReportIssueFlow(StatesGroup):
    report_bot_problem = State()
    report_routes_problem = State()
    report_typo_problem = State()


MainMenuKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                       resize_keyboard=True,
                                       one_time_keyboard=True,
                                       keyboard=[[KeyboardButton(text=ADV_BUTTON_TEXT),
                                                 KeyboardButton(text=QUESTION_BUTTON_TEXT)],
                                                 [KeyboardButton(text=SERVICES_BUTTON_TEXT),
                                                 KeyboardButton(text=REPORT_BUTTON_TEXT)],
                                                 [KeyboardButton(text=OTHER_BUTTON_TEXT)]])

QuestionKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                       resize_keyboard=True,
                                       one_time_keyboard=True,
                                       keyboard=[[KeyboardButton(text=PUBLIC_QUESTION_BUTTON_TEXT),
                                                  KeyboardButton(text=PRIVATE_CONSULTATION_BUTTON_TEXT)]])

AdvKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                  resize_keyboard=True,
                                  one_time_keyboard=True,
                                  keyboard=[[KeyboardButton(text=ADV_OFFER_BUTTON_TEXT)],
                                            [KeyboardButton(text=SPECIAL_OFFER_BUTTON_TEXT)],
                                            [KeyboardButton(text=ADV_IN_CHANNEL_BUTTON_TEXT)]])

ServiceKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                       resize_keyboard=True,
                                       one_time_keyboard=True,
                                       keyboard=[[KeyboardButton(text=BOOK_HOTEL_BUTTON_TEXT)],
                                                 [KeyboardButton(text=ORDER_STATUS_BUTTON_TEXT)],
                                                 [KeyboardButton(text=ORDER_LOUNGE_BUTTON_TEXT)]])

IssueKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                    resize_keyboard=True,
                                    one_time_keyboard=True,
                                    keyboard=[[KeyboardButton(text=REPORT_BOT_PROBLEM_BUTTON_TEXT)],
                                              [KeyboardButton(text=ROUTES_PROBLEM_BUTTON_TEXT)],
                                              [KeyboardButton(text=TYPO_PROBLEM_BUTTON_TEXT)]])


async def get_topic_title(topic_id: int):
    async with TelegramClient("session_name", API_ID, API_HASH) as client:
        peer = await client.get_input_entity(CHAT_PEER_ID)
        result = await client(functions.channels.GetForumTopicsByIDRequest(channel=InputChannel(channel_id=peer.channel_id,
                                                                                                access_hash=peer.access_hash),
                                                                           topics=[topic_id]))
        return result.topics[0].title


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
        error_text = 'Returned feedback error to user with ID=' + str(message.from_user.id) + '. Error: ' + e.__str__()
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

@dp.message(AdvFlow.adv_in_special_offer_state)
async def process_public_question(message: types.Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name=IN_SPECIAL_TOPIC.format(user_name=user_name,
                                                                            user_id=user_id))
    await message.forward(chat_id=CHAT_ID,
                          message_thread_id=forum_topic.message_thread_id)
    await message.reply(text=ADV_OFFER_RECEIVED_TEXT,
                        reply_markup=MainMenuKeyboard)
    await state.clear()


@dp.message(QuestionFlow.public_question)
async def process_public_question(message: types.Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name=PUBLIC_QUESTION_TOPIC.format(user_name=user_name,
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
        if message.text == ADV_BUTTON_TEXT:
            await state.set_state(WelcomeFlow.adv_state)
            await message.reply(text=ADV_STATE_TEXT,
                                parse_mode="html",
                                reply_markup=AdvKeyboard)
        elif message.text == QUESTION_BUTTON_TEXT:
            await state.set_state(WelcomeFlow.questions_state)
            await message.reply(text=QUESTION_STATE_TEXT,
                                parse_mode="html",
                                reply_markup=QuestionKeyboard)
        elif message.text == SERVICES_BUTTON_TEXT:
            await message.reply(text=SERVICE_STATE_TEXT,
                                reply_markup=ServiceKeyboard,
                                parse_mode="html")
        elif message.text == REPORT_BUTTON_TEXT:
            await message.reply(text=SERVICE_STATE_TEXT,
                                reply_markup=IssueKeyboard,
                                parse_mode="html")
        elif message.text == OTHER_BUTTON_TEXT:
            await state.set_state(WelcomeFlow.other_inquiries_state)
            await message.reply(text=OTHER_INQUIRIES_STATE_TEXT)
        elif message.text == ADV_OFFER_BUTTON_TEXT:
            await state.set_state(AdvFlow.adv_in_offer_state)
            await message.reply(ADV_OFFER_STATE_TEXT)
        elif message.text == SPECIAL_OFFER_BUTTON_TEXT:
            await state.set_state(AdvFlow.adv_in_offer_state)
            await message.reply(SPECIAL_OFFER_STATE_TEXT)
        elif message.text == ADV_IN_CHANNEL_BUTTON_TEXT:
            await message.reply(text=ADV_IN_OFFER_TEXT,
                                reply_markup=MainMenuKeyboard,
                                parse_mode="html")
            await state.clear()
        elif message.text == PUBLIC_QUESTION_BUTTON_TEXT:
            await message.reply(PUBLIC_QUESTION_TEXT)
            await state.set_state(QuestionFlow.public_question)
        elif message.text == PRIVATE_CONSULTATION_BUTTON_TEXT:
            await message.reply(text=PRIVATE_CONSULTATION_TEXT,
                                reply_markup=MainMenuKeyboard,
                                parse_mode="html")
            await state.clear()
        elif message.text == BOOK_HOTEL_BUTTON_TEXT:
            await state.set_state(ServicesFlow.services_book_hotel_state)
            await message.reply(
                text=BOOK_HOTEL_TEXT,
                reply_markup=MainMenuKeyboard,
                parse_mode="html")
        elif message.text == ORDER_STATUS_BUTTON_TEXT:
            await state.set_state(ServicesFlow.services_order_status_match_state)
            await message.reply(
                text=ORDER_STATUS_TEXT,
                reply_markup=MainMenuKeyboard,
                parse_mode="html")
        elif message.text == ORDER_LOUNGE_BUTTON_TEXT:
            await state.set_state(ServicesFlow.services_order_lounge)
            await message.reply(
                text=ORDER_LOUNGE_TEXT,
                reply_markup=MainMenuKeyboard,
                parse_mode="html")
        elif message.text == REPORT_BOT_PROBLEM_BUTTON_TEXT:
            await state.set_state(ReportIssueFlow.report_bot_problem)
            await message.reply(text=PROBLEM_TEXT)
        elif message.text == ROUTES_PROBLEM_BUTTON_TEXT:
            await state.set_state(ReportIssueFlow.report_bot_problem)
            await message.reply(text=PROBLEM_TEXT)
        elif message.text == TYPO_PROBLEM_BUTTON_TEXT:
            await state.set_state(ReportIssueFlow.report_bot_problem)
            await message.reply(text=PROBLEM_TEXT)
        elif message.message_thread_id is not None and message.from_user.id != BOT_ID:
            title = await get_topic_title(message.message_thread_id)
            reply_to_chat_id = title.split("[id=")[-1][:-1]
            await bot.send_message(chat_id=reply_to_chat_id,
                                   text=message.text)
        elif message.from_user.id != BOT_ID:
            await message.answer(text=NO_INPUT)
    except Exception as e:
        error_text = 'Returned feedback error to user with ID=' + str(message.from_user.id) + '. Error: ' + e.__str__()
        logging.error(error_text)
        await bot.send_message(text=error_text,
                               chat_id=CHAT_ID,
                               message_thread_id=ERROR_TOPIC_ID)
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
