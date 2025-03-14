from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from literals import *

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
                                                keyboard=[[KeyboardButton(text=STATUS_AVOLTA_RADISSON)]])

IssueKeyboard = ReplyKeyboardMarkup(is_persistent=True,
                                    resize_keyboard=True,
                                    one_time_keyboard=True,
                                    keyboard=[[KeyboardButton(text=REPORT_BOT_PROBLEM_BUTTON_TEXT)],
                                              [KeyboardButton(text=ROUTES_PROBLEM_BUTTON_TEXT)],
                                              [KeyboardButton(text=TYPO_PROBLEM_BUTTON_TEXT)]])

