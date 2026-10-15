import logging
from aiogram import Router, Bot, F
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from states import *
from keyboards import *
from settings import settings
from texts import t, admin_t, texts_under
from topic_registry import create_topic

state_router = Router()
# Customer flows only happen in private chats - keeps stray FSM state from
# ever matching replies sent inside the support group's forum topics.
# Button texts always navigate and are never forwarded as part of an inquiry.
state_router.message.filter(F.chat.type == ChatType.PRIVATE, ~F.text.in_(texts_under("buttons.")))


async def forward_to_topic(bot: Bot, message: Message, album: list[Message] | None, topic_id: int) -> None:
    if album:
        # One call keeps the album grouped and ordered.
        await bot.forward_messages(chat_id=settings.chat_id, from_chat_id=message.chat.id,
                                   message_ids=[m.message_id for m in album], message_thread_id=topic_id)
    else:
        await message.forward(chat_id=settings.chat_id, message_thread_id=topic_id)


async def forward_to_user_topic(message: Message, state: FSMContext, bot: Bot, topic_name: str,
                                received_text: str, album: list[Message] | None = None, reply_markup=None) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    name = topic_name.format(user_name=user_name, user_id=user_id)
    data = await state.get_data()
    if not data:
        topic_id = await create_topic(bot, user=message.from_user, name=name)
        await state.set_data(data={"topic_id": topic_id})
        logging.info(f"Created new forum topic with ID: {topic_id} for user {user_id}")
        await message.reply(text=received_text, reply_markup=reply_markup, parse_mode="html")
    else:
        topic_id = data["topic_id"]
        logging.info(f"Using existing forum topic with ID: {topic_id} for user {user_id}")
    try:
        await forward_to_topic(bot, message, album, topic_id)
    except TelegramBadRequest as e:
        if "message thread not found" not in e.message:
            raise
        # The topic stored in FSM was deleted by an admin - open a new one instead of failing forever.
        old_topic_id = topic_id
        topic_id = await create_topic(bot, user=message.from_user, name=name)
        await state.set_data(data={"topic_id": topic_id})
        logging.warning(f"Forum topic {old_topic_id} for user {user_id} not found, created new topic {topic_id}")
        await bot.send_message(text=f"Forum topic ID={old_topic_id} for user ID={user_id} not found, "
                                    f"created new topic ID={topic_id}",
                               chat_id=settings.chat_id, message_thread_id=settings.error_topic_id)
        await forward_to_topic(bot, message, album, topic_id)

@state_router.message(AdvFlow.adv_in_offer_state)
async def process_public_question(message: Message, state: FSMContext, bot: Bot, album: list[Message] | None = None) -> None:
    logging.info(f"Received message from user {message.from_user.id}, Name: {message.from_user.full_name}, AdvFlow.adv_in_offer_state")
    await forward_to_user_topic(message, state, bot, admin_t("topic.adv"), t("adv.received"), album=album)

@state_router.message(AdvFlow.adv_in_special_offer_state)
async def process_public_question(message: Message, state: FSMContext, bot: Bot, album: list[Message] | None = None) -> None:
    logging.info(f"Received message from user {message.from_user.id}, Name: {message.from_user.full_name}, AdvFlow.adv_in_special_offer_state")
    await forward_to_user_topic(message, state, bot, admin_t("topic.special"), t("adv.received"), album=album)

@state_router.message(ServicesFlow.services_book_hotel_state)
async def process_hotel_request(message: Message, state: FSMContext, bot: Bot, album: list[Message] | None = None) -> None:
    logging.info(f"Received message from user {message.from_user.id}, Name: {message.from_user.full_name}, ServicesFlow.services_book_hotel_state")
    await forward_to_user_topic(message, state, bot, admin_t("topic.hotel"), t("hotel.received"), album=album)

@state_router.message(QuestionFlow.public_question)
async def process_public_question(message: Message, state: FSMContext, bot: Bot, album: list[Message] | None = None) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    topic_id = await create_topic(bot, user=message.from_user,
                                  name=admin_t("topic.public_question").format(user_name=user_name, user_id=user_id))
    logging.info(f"Created public question forum topic for user {user_id} with topic ID: {topic_id}")
    await forward_to_topic(bot, message, album, topic_id)
    await message.reply(text=t("question.sent"), reply_markup=MainMenuKeyboard, parse_mode="html")
    await state.clear()

@state_router.message(WelcomeFlow.other_inquiries_state)
async def process_public_question(message: Message, state: FSMContext, bot: Bot, album: list[Message] | None = None) -> None:
    logging.info(f"Received message from user {message.from_user.id}, Name: {message.from_user.full_name}, WelcomeFlow.other_inquiries_state")
    await forward_to_user_topic(message, state, bot, admin_t("topic.other"), t("question.sent"), album=album, reply_markup=MainMenuKeyboard)
    await state.clear()

@state_router.message(ServicesFlow.services_order_status_avolta_radisson)
async def process_avolta_request(message: Message, state: FSMContext, bot: Bot, album: list[Message] | None = None) -> None:
    logging.info(f"Received message from user {message.from_user.id}, Name: {message.from_user.full_name}, ServiceFlow.services_order_status_avolta_radisson")
    await forward_to_user_topic(message, state, bot, admin_t("topic.avolta"), t("status.received"), album=album)

@state_router.message(ServicesFlow.services_order_status_msc_diamond)
async def process_msc_request(message: Message, state: FSMContext, bot: Bot, album: list[Message] | None = None) -> None:
    logging.info(f"Received message from user {message.from_user.id}, Name: {message.from_user.full_name}, ServicesFlow.services_order_status_msc_diamond")
    await forward_to_user_topic(message, state, bot, admin_t("topic.msc"), t("status.received"), album=album)

@state_router.message(ReportIssueFlow.report_bot_problem)
async def process_public_question(message: Message, state: FSMContext, bot: Bot, album: list[Message] | None = None) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    topic_id = await create_topic(bot, user=message.from_user,
                                  name=admin_t("topic.report_bot").format(user_name=user_name, user_id=user_id))
    logging.info(f"Created bot issue forum topic for user {user_id} with topic ID: {topic_id}")
    await forward_to_topic(bot, message, album, topic_id)
    await message.reply(text=t("report.received"), reply_markup=MainMenuKeyboard, parse_mode="html")
    await state.clear()

@state_router.message(ReportIssueFlow.report_routes_problem)
async def process_public_question(message: Message, state: FSMContext, bot: Bot, album: list[Message] | None = None) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    topic_id = await create_topic(bot, user=message.from_user,
                                  name=admin_t("topic.report_routes").format(user_name=user_name, user_id=user_id))
    logging.info(f"Created routes issue forum topic for user {user_id} with topic ID: {topic_id}")
    await forward_to_topic(bot, message, album, topic_id)
    await message.reply(text=t("report.received"), reply_markup=MainMenuKeyboard, parse_mode="html")
    await state.clear()

@state_router.message(ReportIssueFlow.report_typo_problem)
async def process_public_question(message: Message, state: FSMContext, bot: Bot, album: list[Message] | None = None) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    topic_id = await create_topic(bot, user=message.from_user,
                                  name=admin_t("topic.report_typo").format(user_name=user_name, user_id=user_id))
    logging.info(f"Created typo issue forum topic for user {user_id} with topic ID: {topic_id}")
    await forward_to_topic(bot, message, album, topic_id)
    await message.reply(text=t("report.received"), reply_markup=MainMenuKeyboard, parse_mode="html")
    await state.clear()
