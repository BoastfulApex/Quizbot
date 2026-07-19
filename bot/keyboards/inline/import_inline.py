from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class ImportTargetCallback(CallbackData, prefix="imptgt"):
    mode: str  # "new" | "existing"


def get_import_target_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🆕 Yangi test yarat", callback_data=ImportTargetCallback(mode="new"))
    builder.button(text="📂 Mavjud testga qo'shish", callback_data=ImportTargetCallback(mode="existing"))
    builder.adjust(1)
    return builder.as_markup()
