import logging
import os
import ecs_logging
import asyncio
import sys

from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, InlineKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from telethon import TelegramClient
from telethon.tl import functions
from telethon.tl.types import InputChannel, PeerChat, PeerChannel, InputChannelFromMessage

API_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
CHAT_ID = os.getenv("CHAT_ID")
CHAT_PEER_ID = 2346994241
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
    adv_in_specialoffer_state = State()


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
                                       keyboard=[[KeyboardButton(text="📢Реклама"),
                                                 KeyboardButton(text="🙋‍♂️Задать вопрос")],
                                                 [KeyboardButton(text="🛎️Отели, статусы, лаунжи"),
                                                 KeyboardButton(text="🤖Сообщить о проблеме")],
                                                 [KeyboardButton(text="🌀Прочее")]])

QuestionKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                       resize_keyboard=True,
                                       one_time_keyboard=True,
                                       keyboard=[[KeyboardButton(text="🙋Публичный вопрос"),
                                                  KeyboardButton(text="🙈Частная консультация")]])

AdvKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                  resize_keyboard=True,
                                  one_time_keyboard=True,
                                  keyboard=[[KeyboardButton(text="📥Хотим разместиться у вас (узнать условия)")],
                                            [KeyboardButton(text="⭐️Хотим предложить спецпроект")],
                                            [KeyboardButton(text="📤Хотим предложить размещение в своём канале")]])

ServiceKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                       resize_keyboard=True,
                                       one_time_keyboard=True,
                                       keyboard=[[KeyboardButton(text="🛎️Забронировать отель по спецтарифу")],
                                                 [KeyboardButton(text="✨️Приобрести статус")],
                                                 [KeyboardButton(text="🍸Приобрести проходки в бизнес-залы")]])

IssueKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                       resize_keyboard=True,
                                       one_time_keyboard=True,
                                       keyboard=[[KeyboardButton(text="🤖Проблема с ботом Hilton Negotiated Fares")],
                                                 [KeyboardButton(text="✈️Проблема с routes.de1337ed.ru")],
                                                 [KeyboardButton(text="✍️Опечатка/неточность в тексте")]])


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
        await message.answer(text="<b>👋Добрый день, {user_name}!</b>\nПожалуйста, выберите категорию обращения".
                             format(user_name=user_name),
                             parse_mode="html",
                             reply_markup=MainMenuKeyboard)
    except Exception as e:
        error_text = 'Returned feedback error to user with ID=' + str(message.from_user.id) + '. Error: ' + e.__str__()
        logging.error(error_text)
        await bot.send_message(text=error_text,
                               chat_id=CHAT_ID,
                               message_thread_id=ERROR_TOPIC_ID)
        await message.answer(text="Произошла ошибка, попробуйте позже", parse_mode='html')


@dp.message(AdvFlow.adv_in_offer_state)
async def process_public_question(message: types.Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name="📢Предложение рекламной интеграции от {user_name} [id={user_id}]"
                                               .format(user_name=user_name,
                                                       user_id=user_id))
    await message.forward(chat_id=CHAT_ID,
                          message_thread_id=forum_topic.message_thread_id)
    #   А может кнопочку с коллбеком сюда подсунуть?
    await bot.send_message(chat_id=CHAT_ID,
                           message_thread_id=forum_topic.message_thread_id,
                           text="Не забудь нажать на кнопку, чтобы ответить",
                           reply_markup=InlineKeyboardMarkup(
                               inline_keyboard=[[InlineKeyboardButton(text="Ответить",
                                                                      callback_data=user_id)]]))

    await message.reply(text="✅Спасибо, предложение получено. Я скоро на него отвечу.",
                        reply_markup=MainMenuKeyboard)
    await state.clear()

@dp.message(AdvFlow.adv_in_specialoffer_state)
async def process_public_question(message: types.Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name="⭐️Предложение спецпроекта от {user_name} [id={user_id}]"
                                               .format(user_name=user_name,
                                                       user_id=user_id))
    await message.forward(chat_id=CHAT_ID,
                          message_thread_id=forum_topic.message_thread_id)
    await message.reply(text="✅Спасибо, предложение получено. Я скоро на него отвечу.",
                        reply_markup=MainMenuKeyboard)
    await state.clear()


@dp.message(QuestionFlow.public_question)
async def process_public_question(message: types.Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name="🙋Публичный вопрос от {user_name} [id={user_id}]"
                                               .format(user_name=user_name,
                                                       user_id=user_id))
    await message.forward(chat_id=CHAT_ID,
                          message_thread_id=forum_topic.message_thread_id)
    await message.reply(text="Готово, вопрос отправлен. Ответ придёт сюда же, в диалог с ботом",
                        reply_markup=MainMenuKeyboard)
    await state.clear()



@dp.message(WelcomeFlow.other_inquiries_state)
async def process_public_question(message: types.Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name="🌀Иное от {user_name} [id={user_id}]"
                                               .format(user_name=user_name,
                                                       user_id=user_id))
    await message.forward(chat_id=CHAT_ID,
                          message_thread_id=forum_topic.message_thread_id)
    await message.reply(text="Готово, вопрос отправлен. Ответ придёт сюда же, в диалог с ботом",
                        reply_markup=MainMenuKeyboard)
    await state.clear()

@dp.message(ReportIssueFlow.report_bot_problem)
async def process_public_question(message: types.Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name="🤖Проблема с ботом от {user_name} [id={user_id}]"
                                               .format(user_name=user_name, user_id=user_id))
    await message.forward(chat_id=CHAT_ID,
                          message_thread_id=forum_topic.message_thread_id)
    await message.reply(text="Готово, вопрос отправлен. Ответ придёт сюда же, в диалог с ботом",
                        reply_markup=MainMenuKeyboard)
    await state.clear()

@dp.message(ReportIssueFlow.report_routes_problem)
async def process_public_question(message: types.Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name="✈️Проблема с routes.de1337ed.ru от {user_name} [id={user_id}]"
                                               .format(user_name=user_name, user_id=user_id))
    await message.forward(chat_id=CHAT_ID,
                          message_thread_id=forum_topic.message_thread_id)
    await message.reply(text="Готово, вопрос отправлен. Ответ придёт сюда же, в диалог с ботом",
                        reply_markup=MainMenuKeyboard)
    await state.clear()

@dp.message(ReportIssueFlow.report_typo_problem)
async def process_public_question(message: types.Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    user_name = message.from_user.full_name
    forum_topic = await bot.create_forum_topic(chat_id=CHAT_ID,
                                               name="✍️Опечатка/неточность от {user_name} [id={user_id}]"
                                               .format(user_name=user_name, user_id=user_id))
    await message.forward(chat_id=CHAT_ID,
                          message_thread_id=forum_topic.message_thread_id)
    await message.reply(text="Готово, вопрос отправлен. Ответ придёт сюда же, в диалог с ботом",
                        reply_markup=MainMenuKeyboard)
    await state.clear()


@dp.message()
async def input_handler(message: Message, state: FSMContext) -> None:
    try:
        if message.text == "📢Реклама":
            await state.set_state(WelcomeFlow.adv_state)
            await message.reply(text="Какой тип рекламного сотрудничества вы хотите предложить?",
                                parse_mode="html",
                                reply_markup=AdvKeyboard)
        elif message.text == "🙋‍♂️Задать вопрос":
            await state.set_state(WelcomeFlow.questions_state)
            await message.reply(text="Выберите тип вопроса",
                                parse_mode="html",
                                reply_markup=QuestionKeyboard)
        elif message.text == "🛎️Отели, статусы, лаунжи":
            await message.reply(text="Выберите категорию",
                                reply_markup=ServiceKeyboard,
                                parse_mode="html")
        elif message.text == "🤖Сообщить о проблеме":
            await message.reply(text="Выберите категорию",
                                reply_markup=IssueKeyboard,
                                parse_mode="html")
        elif message.text == "🌀Прочее":
            await state.set_state(WelcomeFlow.other_inquiries_state)
            await message.reply(text="👇Введите ваше обращение ниже:")
        elif message.text == "📥Хотим разместиться у вас (узнать условия)":
            await state.set_state(AdvFlow.adv_in_offer_state)
            await message.reply("Благодарю за интерес к моему каналу! Условия сейчас такие...Если условия вам подходят, оставьте ниже сообщение, в котором укажите:  ")
        elif message.text == "⭐️Хотим предложить спецпроект":
            await state.set_state(AdvFlow.adv_in_offer_state)
            await message.reply("Благодарю за интерес к моему каналу! Спецпроекты - мой любимый формат. Пожалуйста, оставьте ниже сообщение с кратким брифом и я оочень скоро вернусь с предварительной оценкой")
        elif message.text == "📤Хотим предложить размещение в своём канале":
            await message.reply(text="Спасибо, но я не закупаю рекламу",
                                reply_markup=MainMenuKeyboard,
                                parse_mode="html")
            await state.clear()
        elif message.text == "🙋Публичный вопрос":
            await message.reply("Введите вопрос ниже и отправьте боту 👇")
            await state.set_state(QuestionFlow.public_question)
        elif message.text == "🙈Частная консультация":
            await message.reply(text="<b>🙅Я сейчас не даю частные консультации в виду большой занятости.</b>\nЯ напишу в канале, когда это поменяется",
                                reply_markup=MainMenuKeyboard,
                                parse_mode="html")
            await state.clear()
        elif message.text == "🛎️Забронировать отель по спецтарифу":
            await state.set_state(ServicesFlow.services_book_hotel_state)
            await message.reply(
                text="Скоро здесь можно будет забронировать отели по агентским тарифам",
                reply_markup=MainMenuKeyboard,
                parse_mode="html")
        elif message.text == "✨️Приобрести статус":
            await state.set_state(ServicesFlow.services_order_status_match_state)
            await message.reply(
                text="Здесь будут актуальный предложения по получению статусов отельных сетей, авиакомпаний и круизных компаний. Сейчас доступных предложений нет.",
                reply_markup=MainMenuKeyboard,
                parse_mode="html")
        elif message.text == "🍸Приобрести проходки в бизнес-залы":
            await state.set_state(ServicesFlow.services_order_lounge)
            await message.reply(
                text="Здесь будут продаваться мои лишние проходки в бизнес-залы. Сейчас доступных проходок нет",
                reply_markup=MainMenuKeyboard,
                parse_mode="html")
        elif message.text == "🤖Проблема с ботом Hilton Negotiated Fares":
            await state.set_state(ReportIssueFlow.report_bot_problem)
            await message.reply(text="👇Опишите проблему:")
        elif message.text == "✈️Проблема с routes.de1337ed.ru":
            await state.set_state(ReportIssueFlow.report_bot_problem)
            await message.reply(text="👇Опишите проблему:")
        elif message.text == "✍️Опечатка/неточность в тексте":
            await state.set_state(ReportIssueFlow.report_bot_problem)
            await message.reply(text="👇Опишите проблему:")
        elif message.message_thread_id is not None and message.from_user.id != BOT_ID:
            title = await get_topic_title(message.message_thread_id)
            reply_to_chat_id = title.split("[id=")[-1][:-1]
            await bot.send_message(chat_id=reply_to_chat_id,
                                   text=message.text)
        elif message.from_user.id != BOT_ID:
            await message.answer("Сначала выберите тему обращения. Чтобы увидеть список тем, нажмите /start")
    except Exception as e:
        error_text = 'Returned feedback error to user with ID=' + str(message.from_user.id) + '. Error: ' + e.__str__()
        logging.error(error_text)
        await bot.send_message(text=error_text,
                               chat_id=CHAT_ID,
                               message_thread_id=ERROR_TOPIC_ID)
        await message.answer(text="Произошла ошибка, попробуйте позже", parse_mode='html')



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
