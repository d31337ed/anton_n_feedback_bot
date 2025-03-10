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

API_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
LOG_PATH = './logs/feedback_bot.log'
ERROR_TOPIC_ID = 27

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
    adv_in_offer_conditions_state = State()
    adv_in_offer_input_state = State()


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

QuestionKeyboard = [[KeyboardButton(text="🙋Публичный вопрос"),
                    KeyboardButton(text="🙈Частная консультация")]]


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
    await message.reply("Готово, вопрос отправлен. Ответ придёт сюда же, в диалог с ботом")
    await state.clear()


@dp.message()
async def input_handler(message: Message, state: FSMContext) -> None:
    try:
        if message.text == "📢Реклама":
            await state.set_state(WelcomeFlow.adv_state)
        elif message.text == "🙋‍♂️Задать вопрос":
            await state.set_state(WelcomeFlow.questions_state)
            await message.reply(text="Выберите тип вопроса",
                                parse_mode="html",
                                reply_markup=ReplyKeyboardMarkup(
                                    is_persistent=True,
                                    resize_keyboard=True,
                                    one_time_keyboard=True,
                                    keyboard=QuestionKeyboard))
        elif message.text == "🛎️Отели, статусы, лаунжи":
            await state.set_state(WelcomeFlow.services_state)
        elif message.text == "🤖Сообщить о проблеме":
            await state.set_state(WelcomeFlow.report_issue_state)
        elif message.text == "🌀Прочее":
            await state.set_state(WelcomeFlow.other_inquiries_state)
        elif message.text == "🙋Публичный вопрос":
            await message.reply("Введите вопрос ниже и отправьте боту 👇")
            await state.set_state(QuestionFlow.public_question)
        elif message.text == "🙈Частная консультация":
            await message.reply(text="<b>🙅Я сейчас не даю частные консультации в виду большой занятости.</b>\nЯ напишу в канале, когда это поменяется",
                                reply_markup=MainMenuKeyboard,
                                parse_mode="html")
            await state.set_state(QuestionFlow.public_question)
        elif message.from_user.id != int(API_TOKEN.split(":")[0]):
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
