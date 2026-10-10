from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from keyboards import HOTEL_RULES_CALLBACK, HOTEL_COLLAPSE_CALLBACK, HotelEntryKeyboard, HotelRulesKeyboard
from literals import HOTEL_ENTRY_TEXT, HOTEL_RULES_TEXT

callback_router = Router()


async def edit_hotel_entry(callback: CallbackQuery, text: str, keyboard) -> None:
    try:
        await callback.message.edit_text(text=text, parse_mode="html", reply_markup=keyboard,
                                         link_preview_options={"is_disabled": True})
    except TelegramBadRequest as e:
        # A double tap edits the message to the text it already has.
        if "message is not modified" not in e.message:
            raise
    await callback.answer()


@callback_router.callback_query(F.data == HOTEL_RULES_CALLBACK)
async def hotel_rules_callback(callback: CallbackQuery) -> None:
    await edit_hotel_entry(callback, HOTEL_RULES_TEXT, HotelRulesKeyboard)


@callback_router.callback_query(F.data == HOTEL_COLLAPSE_CALLBACK)
async def hotel_collapse_callback(callback: CallbackQuery) -> None:
    await edit_hotel_entry(callback, HOTEL_ENTRY_TEXT, HotelEntryKeyboard)
