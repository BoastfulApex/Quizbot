from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class VisibilityCallback(CallbackData, prefix="qvis"):
    value: str


class QuizAddMoreCallback(CallbackData, prefix="qmore"):
    action: str


class QuizSelectCallback(CallbackData, prefix="qsel"):
    quiz_id: int


class QuizReadyCallback(CallbackData, prefix="qready"):
    quiz_id: int


class QuizRetryCallback(CallbackData, prefix="qretry"):
    quiz_id: int


def get_visibility_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔒 Shaxsiy (Private)", callback_data=VisibilityCallback(value="private"))
    builder.button(text="🌐 Ommaviy (Public)", callback_data=VisibilityCallback(value="public"))
    builder.adjust(1)
    return builder.as_markup()


def get_add_more_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Yana savol qo'shish", callback_data=QuizAddMoreCallback(action="add"))
    builder.button(text="✅ Testni yakunlash", callback_data=QuizAddMoreCallback(action="finish"))
    builder.adjust(1)
    return builder.as_markup()


def get_quiz_list_keyboard(quizzes: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for quiz_id, title in quizzes:
        label = title if len(title) <= 40 else title[:37] + "..."
        builder.button(text=label, callback_data=QuizSelectCallback(quiz_id=quiz_id))
    builder.adjust(1)
    return builder.as_markup()


def get_ready_keyboard(quiz_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Men tayyorman!", callback_data=QuizReadyCallback(quiz_id=quiz_id))
    return builder.as_markup()


def get_result_keyboard(quiz_id: int, bot_username: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Qaytadan urinish", callback_data=QuizRetryCallback(quiz_id=quiz_id))
    builder.button(
        text="👥 Guruhda testni boshlash",
        url=f"https://t.me/{bot_username}?startgroup=quiz_{quiz_id}",
    )
    builder.button(text="📤 Testni ulashish", switch_inline_query=f"quiz:{quiz_id}")
    builder.adjust(1)
    return builder.as_markup()


def get_inline_start_keyboard(quiz_id: int, bot_username: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Testni boshlash", url=f"https://t.me/{bot_username}?start=quiz_{quiz_id}")
    return builder.as_markup()
