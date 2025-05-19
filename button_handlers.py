from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from keyboards import MainMenuKeyboard, QuestionKeyboard, AdvKeyboard, ServiceKeyboard, IssueKeyboard, \
    AvailableStatusesKeyboard
from states import WelcomeFlow, AdvFlow, ServicesFlow, QuestionFlow, ReportIssueFlow
from literals import *

async def handle_adv_button(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data:
        await state.set_state(WelcomeFlow.adv_state)
        await message.reply(text=ADV_STATE_TEXT, parse_mode="html", reply_markup=AdvKeyboard)
    else:
        await message.reply(text=DUPLICATED_ERROR, parse_mode="html")

async def handle_question_button(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data:
        await state.set_state(WelcomeFlow.questions_state)
        await message.reply(text=QUESTION_STATE_TEXT, parse_mode="html", reply_markup=QuestionKeyboard)
    else:
        await message.reply(text=DUPLICATED_ERROR, parse_mode="html")

async def handle_services_button(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data:
        await state.set_state(WelcomeFlow.services_state)
        await message.reply(text=SERVICE_STATE_TEXT, reply_markup=ServiceKeyboard, parse_mode="html")
    else:
        await message.reply(text=DUPLICATED_ERROR, parse_mode="html")

async def handle_report_button(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data:
        await state.set_state(WelcomeFlow.report_issue_state)
        await message.reply(text=SERVICE_STATE_TEXT, reply_markup=IssueKeyboard, parse_mode="html")
    else:
        await message.reply(text=DUPLICATED_ERROR, parse_mode="html")

async def handle_other_button(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data:
        await state.set_state(WelcomeFlow.other_inquiries_state)
        await message.reply(text=OTHER_INQUIRIES_STATE_TEXT, parse_mode="html")
    else:
        await message.reply(text=DUPLICATED_ERROR, parse_mode="html")

async def handle_adv_offer_button(message: Message, state: FSMContext):
    await state.set_state(AdvFlow.adv_in_offer_state)
    await message.reply(ADV_OFFER_STATE_TEXT, parse_mode="html")

async def handle_special_offer_button(message: Message, state: FSMContext):
    await state.set_state(AdvFlow.adv_in_special_offer_state)
    await message.reply(SPECIAL_OFFER_STATE_TEXT, parse_mode="html")

async def handle_adv_in_channel_button(message: Message, state: FSMContext):
    await message.reply(text=ADV_IN_OFFER_TEXT, reply_markup=MainMenuKeyboard, parse_mode="html")
    await state.clear()

async def handle_public_question_button(message: Message, state: FSMContext):
    await message.reply(PUBLIC_QUESTION_TEXT, parse_mode="html")
    await state.set_state(QuestionFlow.public_question)

async def handle_private_consultation_button(message: Message, state: FSMContext):
    await message.reply(text=PRIVATE_CONSULTATION_TEXT, reply_markup=MainMenuKeyboard, parse_mode="html")
    await state.clear()

async def handle_book_hotel_button(message: Message, state: FSMContext):
    await state.set_state(ServicesFlow.services_book_hotel_state)
    await message.reply(text=BOOK_HOTEL_TEXT, parse_mode="html",
                        link_preview_options={"is_disabled": True})

async def handle_order_status_button(message: Message, state: FSMContext):
    await state.set_state(ServicesFlow.services_order_status_match_state)
    await message.reply(text=ORDER_STATUS_TEXT, reply_markup=AvailableStatusesKeyboard, parse_mode="html",
                        link_preview_options={"is_disabled": True})

async def handle_status_avolta_radisson(message: Message, state: FSMContext):
    await state.set_state(ServicesFlow.services_order_status_avolta_radisson)
    await message.reply(text=ORDER_STATUS_CERTAIN_TEXT, parse_mode="html")

async def handle_status_msc_diamond(message: Message, state: FSMContext):
    await state.set_state(ServicesFlow.services_order_status_msc_diamond)
    await message.reply(text=ORDER_STATUS_CERTAIN_TEXT, parse_mode="html")

async def handle_order_lounge_button(message: Message, state: FSMContext):
    await state.set_state(ServicesFlow.services_order_lounge)
    await message.reply(text=ORDER_LOUNGE_TEXT, reply_markup=MainMenuKeyboard, parse_mode="html")

async def handle_report_bot_problem_button(message: Message, state: FSMContext):
    await state.set_state(ReportIssueFlow.report_bot_problem)
    await message.reply(text=PROBLEM_TEXT)

async def handle_routes_problem_button(message: Message, state: FSMContext):
    await state.set_state(ReportIssueFlow.report_routes_problem)
    await message.reply(text=PROBLEM_TEXT)

async def handle_typo_problem_button(message: Message, state: FSMContext):
    await state.set_state(ReportIssueFlow.report_typo_problem)
    await message.reply(text=PROBLEM_TEXT)

# States-to-button dictionary
handlers = {
    ADV_BUTTON_TEXT: handle_adv_button,
    QUESTION_BUTTON_TEXT: handle_question_button,
    SERVICES_BUTTON_TEXT: handle_services_button,
    REPORT_BUTTON_TEXT: handle_report_button,
    OTHER_BUTTON_TEXT: handle_other_button,
    ADV_OFFER_BUTTON_TEXT: handle_adv_offer_button,
    SPECIAL_OFFER_BUTTON_TEXT: handle_special_offer_button,
    ADV_IN_CHANNEL_BUTTON_TEXT: handle_adv_in_channel_button,
    PUBLIC_QUESTION_BUTTON_TEXT: handle_public_question_button,
    PRIVATE_CONSULTATION_BUTTON_TEXT: handle_private_consultation_button,
    BOOK_HOTEL_BUTTON_TEXT: handle_book_hotel_button,
    ORDER_STATUS_BUTTON_TEXT: handle_order_status_button,
    STATUS_AVOLTA_RADISSON: handle_status_avolta_radisson,
    STATUS_MSC_DIAMOND: handle_status_msc_diamond,
    ORDER_LOUNGE_BUTTON_TEXT: handle_order_lounge_button,
    REPORT_BOT_PROBLEM_BUTTON_TEXT: handle_report_bot_problem_button,
    ROUTES_PROBLEM_BUTTON_TEXT: handle_routes_problem_button,
    TYPO_PROBLEM_BUTTON_TEXT: handle_typo_problem_button,
}