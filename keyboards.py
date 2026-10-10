from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from literals import *
from settings import settings

# Callback data of the hotel entry message.
HOTEL_RULES_CALLBACK = "hotel:rules"
HOTEL_COLLAPSE_CALLBACK = "hotel:collapse"

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

AvailableStatusesKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                                resize_keyboard=True,
                                                one_time_keyboard=True,
                                                keyboard=[[KeyboardButton(text=STATUS_AVOLTA_RADISSON)],
                                                          [KeyboardButton(text=STATUS_MSC_DIAMOND)]])

IssueKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                    resize_keyboard=True,
                                    one_time_keyboard=True,
                                    keyboard=[[KeyboardButton(text=REPORT_BOT_PROBLEM_BUTTON_TEXT)],
                                              [KeyboardButton(text=ROUTES_PROBLEM_BUTTON_TEXT)],
                                              [KeyboardButton(text=TYPO_PROBLEM_BUTTON_TEXT)]])


def hotel_form_button(text: str, query: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, web_app=WebAppInfo(url=f"{settings.webapp_url}?{query}"))


HotelEntryKeyboard = InlineKeyboardMarkup(inline_keyboard=[
    [hotel_form_button(HOTEL_FORM_BUTTON_TEXT, "mode=new")],
    [InlineKeyboardButton(text=HOTEL_RULES_BUTTON_TEXT, callback_data=HOTEL_RULES_CALLBACK)]])

HotelRulesKeyboard = InlineKeyboardMarkup(inline_keyboard=[
    [hotel_form_button(HOTEL_FORM_ALT_BUTTON_TEXT, "mode=new")],
    [InlineKeyboardButton(text=HOTEL_COLLAPSE_BUTTON_TEXT, callback_data=HOTEL_COLLAPSE_CALLBACK)]])


def hotel_edit_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[hotel_form_button(HOTEL_EDIT_BUTTON_TEXT, f"request_id={request_id}")]])
