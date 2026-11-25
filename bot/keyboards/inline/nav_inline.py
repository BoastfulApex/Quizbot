from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class NavCallback(CallbackData, prefix="nav"):
    action: str  # "back" | "cancel" | "close"


BTN_BACK_TEXT = "⬅️ Orqaga"
BTN_CANCEL_TEXT = "❌ Bekor qilish"
BTN_CLOSE_TEXT = "✖️ Yopish"


def nav_row(*, back: bool = True, cancel: bool = True, close: bool = False) -> list[InlineKeyboardButton]:
    row: list[InlineKeyboardButton] = []
    if back:
        row.append(InlineKeyboardButton(text=BTN_BACK_TEXT, callback_data=NavCallback(action="back").pack()))
    if cancel:
        row.append(InlineKeyboardButton(text=BTN_CANCEL_TEXT, callback_data=NavCallback(action="cancel").pack()))
    if close:
        row.append(InlineKeyboardButton(text=BTN_CLOSE_TEXT, callback_data=NavCallback(action="close").pack()))
    return row


def with_nav(
    markup: InlineKeyboardMarkup | None = None,
    *,
    back: bool = True,
    cancel: bool = True,
    close: bool = False,
) -> InlineKeyboardMarkup:
    """Mavjud inline klaviaturaning oxiriga navigatsiya qatorini qo'shadi."""
    rows = list(markup.inline_keyboard) if markup else []
    row = nav_row(back=back, cancel=cancel, close=close)
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)
