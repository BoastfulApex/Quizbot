import logging

from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from bot.keyboards.inline.quiz_inline import get_inline_start_keyboard
from services.quiz_service import count_questions, get_quiz_by_id, get_user_and_public_quizzes
from services.user_service import get_or_create_user

logger = logging.getLogger(__name__)
router = Router(name="inline_query")

_bot_username_cache: str | None = None


async def _get_bot_username(bot) -> str:
    global _bot_username_cache
    if _bot_username_cache is None:
        me = await bot.get_me()
        _bot_username_cache = me.username
    return _bot_username_cache


def _build_result(quiz, questions_count: int, bot_username: str) -> InlineQueryResultArticle:
    description = f"{questions_count} ta savol · {quiz.time_per_question_sec} soniya"
    text = (
        f"📋 <b>{quiz.title}</b>\n\n"
        f"❓ {questions_count} ta savol\n"
        f"⏱ Har bir savol uchun {quiz.time_per_question_sec} soniya"
    )
    return InlineQueryResultArticle(
        id=str(quiz.id),
        title=quiz.title,
        description=description,
        input_message_content=InputTextMessageContent(message_text=text, parse_mode="HTML"),
        reply_markup=get_inline_start_keyboard(quiz.id, bot_username),
    )


@router.inline_query()
async def handle_inline_query(inline_query: InlineQuery, bot) -> None:
    bot_username = await _get_bot_username(bot)
    query = inline_query.query.strip()

    results = []
    if query.startswith("quiz:"):
        raw_id = query[5:].strip()
        if raw_id.isdigit():
            quiz = await get_quiz_by_id(int(raw_id))
            if quiz is not None:
                count = await count_questions(quiz.id)
                results.append(_build_result(quiz, count, bot_username))
    else:
        user = await get_or_create_user(inline_query.from_user.id, inline_query.from_user.username)
        if user is not None:
            quizzes = await get_user_and_public_quizzes(user.id)
            for quiz in quizzes[:20]:
                count = await count_questions(quiz.id)
                results.append(_build_result(quiz, count, bot_username))

    await bot.answer_inline_query(inline_query.id, results=results, cache_time=5, is_personal=True)
