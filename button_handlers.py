from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import Message

from keyboards import MainMenuKeyboard, QuestionKeyboard, AdvKeyboard, ServiceKeyboard, IssueKeyboard, \
    AvailableStatusesKeyboard, HotelEntryKeyboard
from states import WelcomeFlow, AdvFlow, ServicesFlow, QuestionFlow, ReportIssueFlow
from texts import t

async def blocked_by_active_inquiry(message: Message, state: FSMContext, target: State | None) -> bool:
    # A user with an open topic may only re-enter the branch that owns it,
    # otherwise the next message would land in that topic under the wrong flow.
    if not await state.get_data() or (target is not None and await state.get_state() == target.state):
        return False
    await message.reply(text=t("common.inquiry_open"), parse_mode="html")
    return True

async def handle_adv_button(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data:
        await state.set_state(WelcomeFlow.adv_state)
        await message.reply(text=t("menu.adv"), parse_mode="html", reply_markup=AdvKeyboard)
    else:
        await message.reply(text=t("common.inquiry_open"), parse_mode="html")

async def handle_question_button(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data:
        await state.set_state(WelcomeFlow.questions_state)
        await message.reply(text=t("menu.question"), parse_mode="html", reply_markup=QuestionKeyboard)
    else:
        await message.reply(text=t("common.inquiry_open"), parse_mode="html")

async def handle_services_button(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data:
        await state.set_state(WelcomeFlow.services_state)
        await message.reply(text=t("menu.services"), reply_markup=ServiceKeyboard, parse_mode="html")
    else:
        await message.reply(text=t("common.inquiry_open"), parse_mode="html")

async def handle_report_button(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data:
        await state.set_state(WelcomeFlow.report_issue_state)
        await message.reply(text=t("menu.report"), reply_markup=IssueKeyboard, parse_mode="html")
    else:
        await message.reply(text=t("common.inquiry_open"), parse_mode="html")

async def handle_other_button(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data:
        await state.set_state(WelcomeFlow.other_inquiries_state)
        await message.reply(text=t("menu.other"), parse_mode="html")
    else:
        await message.reply(text=t("common.inquiry_open"), parse_mode="html")

async def handle_adv_offer_button(message: Message, state: FSMContext):
    if await blocked_by_active_inquiry(message, state, AdvFlow.adv_in_offer_state):
        return
    await state.set_state(AdvFlow.adv_in_offer_state)
    await message.reply(t("adv.offer"), parse_mode="html")

async def handle_special_offer_button(message: Message, state: FSMContext):
    if await blocked_by_active_inquiry(message, state, AdvFlow.adv_in_special_offer_state):
        return
    await state.set_state(AdvFlow.adv_in_special_offer_state)
    await message.reply(t("adv.special"), parse_mode="html")

async def handle_adv_in_channel_button(message: Message, state: FSMContext):
    if await blocked_by_active_inquiry(message, state, None):
        return
    await message.reply(text=t("adv.in_channel"), reply_markup=MainMenuKeyboard, parse_mode="html")
    await state.clear()

async def handle_public_question_button(message: Message, state: FSMContext):
    if await blocked_by_active_inquiry(message, state, QuestionFlow.public_question):
        return
    await message.reply(t("question.public"), parse_mode="html")
    await state.set_state(QuestionFlow.public_question)

async def handle_private_consultation_button(message: Message, state: FSMContext):
    if await blocked_by_active_inquiry(message, state, None):
        return
    await message.reply(text=t("question.private"), reply_markup=MainMenuKeyboard, parse_mode="html")
    await state.clear()

async def handle_book_hotel_button(message: Message, state: FSMContext):
    if await blocked_by_active_inquiry(message, state, ServicesFlow.services_book_hotel_state):
        return
    await state.set_state(ServicesFlow.services_book_hotel_state)
    await message.reply(text=t("hotel.entry"), parse_mode="html", reply_markup=HotelEntryKeyboard)

async def handle_order_status_button(message: Message, state: FSMContext):
    if await blocked_by_active_inquiry(message, state, ServicesFlow.services_order_status_match_state):
        return
    await state.set_state(ServicesFlow.services_order_status_match_state)
    await message.reply(text=t("status.list"), reply_markup=AvailableStatusesKeyboard, parse_mode="html",
                        link_preview_options={"is_disabled": True})

async def handle_status_avolta_radisson(message: Message, state: FSMContext):
    if await blocked_by_active_inquiry(message, state, ServicesFlow.services_order_status_avolta_radisson):
        return
    await state.set_state(ServicesFlow.services_order_status_avolta_radisson)
    await message.reply(text=t("status.chosen"), parse_mode="html")

async def handle_status_msc_diamond(message: Message, state: FSMContext):
    if await blocked_by_active_inquiry(message, state, ServicesFlow.services_order_status_msc_diamond):
        return
    await state.set_state(ServicesFlow.services_order_status_msc_diamond)
    await message.reply(text=t("status.chosen"), parse_mode="html")

async def handle_order_lounge_button(message: Message, state: FSMContext):
    if await blocked_by_active_inquiry(message, state, ServicesFlow.services_order_lounge):
        return
    await state.set_state(ServicesFlow.services_order_lounge)
    await message.reply(text=t("lounge.list"), reply_markup=MainMenuKeyboard, parse_mode="html")

async def handle_report_bot_problem_button(message: Message, state: FSMContext):
    if await blocked_by_active_inquiry(message, state, ReportIssueFlow.report_bot_problem):
        return
    await state.set_state(ReportIssueFlow.report_bot_problem)
    await message.reply(text=t("report.describe"))

async def handle_routes_problem_button(message: Message, state: FSMContext):
    if await blocked_by_active_inquiry(message, state, ReportIssueFlow.report_routes_problem):
        return
    await state.set_state(ReportIssueFlow.report_routes_problem)
    await message.reply(text=t("report.describe"))

async def handle_typo_problem_button(message: Message, state: FSMContext):
    if await blocked_by_active_inquiry(message, state, ReportIssueFlow.report_typo_problem):
        return
    await state.set_state(ReportIssueFlow.report_typo_problem)
    await message.reply(text=t("report.describe"))

# Button text keys (see texts.text_key) to handlers.
handlers = {
    "buttons.main.adv": handle_adv_button,
    "buttons.main.question": handle_question_button,
    "buttons.main.services": handle_services_button,
    "buttons.main.report": handle_report_button,
    "buttons.main.other": handle_other_button,
    "buttons.adv.offer": handle_adv_offer_button,
    "buttons.adv.special": handle_special_offer_button,
    "buttons.adv.in_channel": handle_adv_in_channel_button,
    "buttons.question.public": handle_public_question_button,
    "buttons.question.private": handle_private_consultation_button,
    "buttons.services.hotel": handle_book_hotel_button,
    "buttons.services.status": handle_order_status_button,
    "buttons.status.avolta": handle_status_avolta_radisson,
    "buttons.status.msc": handle_status_msc_diamond,
    "buttons.services.lounge": handle_order_lounge_button,
    "buttons.report.bot": handle_report_bot_problem_button,
    "buttons.report.routes": handle_routes_problem_button,
    "buttons.report.typo": handle_typo_problem_button,
}