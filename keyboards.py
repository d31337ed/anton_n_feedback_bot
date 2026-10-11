from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from settings import settings
from texts import t

# Callback data of the hotel entry message.
HOTEL_RULES_CALLBACK = "hotel:rules"
HOTEL_COLLAPSE_CALLBACK = "hotel:collapse"

MainMenuKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                       resize_keyboard=True,
                                       one_time_keyboard=True,
                                       keyboard=[[KeyboardButton(text=t("buttons.main.adv")),
                                                 KeyboardButton(text=t("buttons.main.question"))],
                                                 [KeyboardButton(text=t("buttons.main.services")),
                                                 KeyboardButton(text=t("buttons.main.report"))],
                                                 [KeyboardButton(text=t("buttons.main.other"))]])

QuestionKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                       resize_keyboard=True,
                                       one_time_keyboard=True,
                                       keyboard=[[KeyboardButton(text=t("buttons.question.public")),
                                                  KeyboardButton(text=t("buttons.question.private"))]])

AdvKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                  resize_keyboard=True,
                                  one_time_keyboard=True,
                                  keyboard=[[KeyboardButton(text=t("buttons.adv.offer"))],
                                            [KeyboardButton(text=t("buttons.adv.special"))],
                                            [KeyboardButton(text=t("buttons.adv.in_channel"))]])

ServiceKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                       resize_keyboard=True,
                                       one_time_keyboard=True,
                                       keyboard=[[KeyboardButton(text=t("buttons.services.hotel"))],
                                                 [KeyboardButton(text=t("buttons.services.status"))],
                                                 [KeyboardButton(text=t("buttons.services.lounge"))]])

AvailableStatusesKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                                resize_keyboard=True,
                                                one_time_keyboard=True,
                                                keyboard=[[KeyboardButton(text=t("buttons.status.avolta"))],
                                                          [KeyboardButton(text=t("buttons.status.msc"))]])

IssueKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                    resize_keyboard=True,
                                    one_time_keyboard=True,
                                    keyboard=[[KeyboardButton(text=t("buttons.report.bot"))],
                                              [KeyboardButton(text=t("buttons.report.routes"))],
                                              [KeyboardButton(text=t("buttons.report.typo"))]])


def hotel_form_button(text: str, query: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, web_app=WebAppInfo(url=f"{settings.webapp_url}?{query}"))


HotelEntryKeyboard = InlineKeyboardMarkup(inline_keyboard=[
    [hotel_form_button(t("hotel.form_button"), "mode=new")],
    [InlineKeyboardButton(text=t("hotel.rules_button"), callback_data=HOTEL_RULES_CALLBACK)]])

HotelRulesKeyboard = InlineKeyboardMarkup(inline_keyboard=[
    [hotel_form_button(t("hotel.form_alt_button"), "mode=new")],
    [InlineKeyboardButton(text=t("hotel.collapse_button"), callback_data=HOTEL_COLLAPSE_CALLBACK)]])


def hotel_edit_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[hotel_form_button(t("hotel.edit_button"), f"request_id={request_id}")]])
