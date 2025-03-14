import logging
from os import getenv
from aiogram import Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from dotenv import load_dotenv

from states import *
from keyboards import *

load_dotenv()

API_TOKEN = getenv("BOT_TOKEN")
CHAT_ID = getenv("CHAT_ID")
LOG_PATH = './logs/feedback_bot.log'
ERROR_TOPIC_ID = int(getenv("ERROR_TOPIC_ID"))
BOT_ID = int(API_TOKEN.split(":")[0])

state_router = Router()

@state_router.message(AdvFlow.adv_in_offer_state)
async def process_public_question(message: Message, state: FSMContext, bot: Bot) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    data = await state.get_data()
    logging.info(f"Received message from user {user_id}, Name: {user_name}, AdvFlow.adv_in_offer_state")
    if not data:
        forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                                   name=IN_ADV_TOPIC.format(user_name=user_name,
                                                                            user_id=user_id))
        topic_id = forum_topic.message_thread_id
        await state.set_data(data={"topic_id": forum_topic.message_thread_id})
        logging.info(f"Created new forum topic with ID: {topic_id} for user {user_id}")
        await message.reply(text=ADV_OFFER_RECEIVED_TEXT, parse_mode="html")
    else:
        topic_id = data["topic_id"]
        logging.info(f"Using existing forum topic with ID: {topic_id} for user {user_id}")
    await message.forward(chat_id=CHAT_ID, message_thread_id=topic_id)

@state_router.message(AdvFlow.adv_in_special_offer_state)
async def process_public_question(message: Message, state: FSMContext, bot: Bot) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    data = await state.get_data()
    logging.info(f"Received message from user {user_id}, Name: {user_name}, AdvFlow.adv_in_special_offer_state")
    if not data:
        forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                                   name=IN_SPECIAL_TOPIC.format(user_name=user_name,
                                                                            user_id=user_id))
        topic_id = forum_topic.message_thread_id
        await state.set_data(data={"topic_id": forum_topic.message_thread_id})
        logging.info(f"Created new forum topic with ID: {topic_id} for user {user_id}")
        await message.reply(text=ADV_OFFER_RECEIVED_TEXT, parse_mode="html")
    else:
        topic_id = data["topic_id"]
        logging.info(f"Using existing forum topic with ID: {topic_id} for user {user_id}")
    await message.forward(chat_id=CHAT_ID, message_thread_id=topic_id)

@state_router.message(ServicesFlow.services_book_hotel_state)
async def process_hotel_request(message: Message, state: FSMContext, bot: Bot) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    data = await state.get_data()
    logging.info(f"Received message from user {user_id}, Name: {user_name}, ServicesFlow.services_book_hotel_state")
    if not data:
        forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                                   name=HOTEL_REQUEST_TOPIC.format(user_name=user_name,
                                                                                   user_id=user_id))
        topic_id = forum_topic.message_thread_id
        await state.set_data(data={"topic_id": forum_topic.message_thread_id})
        logging.info(f"Created new forum topic with ID: {topic_id} for user {user_id}")
        await message.reply(text=HOTEL_REQUEST_RECEIVED_TEXT, parse_mode="html")
    else:
        topic_id = data["topic_id"]
        logging.info(f"Using existing forum topic with ID: {topic_id} for user {user_id}")
    await message.forward(chat_id=CHAT_ID, message_thread_id=topic_id)

@state_router.message(QuestionFlow.public_question)
async def process_public_question(message: Message, state: FSMContext, bot: Bot) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID, name=PUBLIC_QUESTION_TOPIC.format(user_name=user_name,
                                                                                                  user_id=user_id))
    logging.info(f"Created public question forum topic for user {user_id} with topic ID: {forum_topic.message_thread_id}")
    await message.forward(chat_id=CHAT_ID, message_thread_id=forum_topic.message_thread_id)
    await message.reply(text=INQUIRY_SENT_TEXT, reply_markup=MainMenuKeyboard, parse_mode="html")
    await state.clear()

@state_router.message(WelcomeFlow.other_inquiries_state)
async def process_public_question(message: Message, state: FSMContext, bot: Bot) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    data = await state.get_data()
    logging.info(f"Received message from user {user_id}, Name: {user_name}, WelcomeFlow.other_inquiries_state")
    if not data:
        forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                                   name=OTHERS_TOPIC.format(user_name=user_name,
                                                                            user_id=user_id))
        topic_id = forum_topic.message_thread_id
        await state.set_data(data={"topic_id": topic_id})
        logging.info(f"Created new forum topic with ID: {topic_id} for user {user_id}")
        await message.reply(text=INQUIRY_SENT_TEXT, parse_mode="html")
    else:
        topic_id = data["topic_id"]
        logging.info(f"Using existing forum topic with ID: {topic_id} for user {user_id}")
    await message.forward(chat_id=CHAT_ID, message_thread_id=topic_id)

@state_router.message(ServicesFlow.services_order_status_avolta_radisson)
async def process_avolta_request(message: Message, state: FSMContext, bot: Bot) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    data = await state.get_data()
    logging.info(f"Received message from user {user_id}, Name: {user_name}, ServiceFlow.services_order_status_avolta_radisson")
    if not data:
        forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                                   name=AVOLTA_TOPIC.format(user_name=user_name,
                                                                            user_id=user_id))
        topic_id = forum_topic.message_thread_id
        await state.set_data(data={"topic_id": topic_id})
        logging.info(f"Created new forum topic with ID: {topic_id} for user {user_id}")
        await message.reply(text=INQUIRY_SENT_TEXT, parse_mode="html")
    else:
        topic_id = data["topic_id"]
        logging.info(f"Using existing forum topic with ID: {topic_id} for user {user_id}")
    await message.forward(chat_id=CHAT_ID, message_thread_id=topic_id)

@state_router.message(ReportIssueFlow.report_bot_problem)
async def process_public_question(message: Message, state: FSMContext, bot: Bot) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name=ISSUE_BOT_TOPIC.format(user_name=user_name,
                                                                           user_id=user_id))
    logging.info(f"Created bot issue forum topic for user {user_id} with topic ID: {forum_topic.message_thread_id}")
    await message.forward(chat_id=CHAT_ID, message_thread_id=forum_topic.message_thread_id)
    await message.reply(text=PROBLEM_RECEIVED_TEXT, reply_markup=MainMenuKeyboard, parse_mode="html")
    await state.clear()

@state_router.message(ReportIssueFlow.report_routes_problem)
async def process_public_question(message: Message, state: FSMContext, bot: Bot) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name=ISSUE_ROUTES_TOPIC.format(user_name=user_name,
                                                                              user_id=user_id))
    logging.info(f"Created routes issue forum topic for user {user_id} with topic ID: {forum_topic.message_thread_id}")
    await message.forward(chat_id=CHAT_ID, message_thread_id=forum_topic.message_thread_id)
    await message.reply(text=PROBLEM_RECEIVED_TEXT, reply_markup=MainMenuKeyboard, parse_mode="html")
    await state.clear()

@state_router.message(ReportIssueFlow.report_typo_problem)
async def process_public_question(message: Message, state: FSMContext, bot: Bot) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name=ISSUE_TYPO_TOPIC.format(user_name=user_name, user_id=user_id))
    logging.info(f"Created typo issue forum topic for user {user_id} with topic ID: {forum_topic.message_thread_id}")
    await message.forward(chat_id=CHAT_ID, message_thread_id=forum_topic.message_thread_id)
    await message.reply(text=PROBLEM_RECEIVED_TEXT, reply_markup=MainMenuKeyboard, parse_mode="html")
    await state.clear()
