from aiogram.fsm.state import State, StatesGroup


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
    services_hotel_input_state = State()


class QuestionFlow(StatesGroup):
    public_question = State()
    private_question = State()


class ReportIssueFlow(StatesGroup):
    report_bot_problem = State()
    report_routes_problem = State()
    report_typo_problem = State()
