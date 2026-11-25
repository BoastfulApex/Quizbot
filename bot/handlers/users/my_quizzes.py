import asyncio
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, Message

from apps.users.models import User
from bot.keyboards.default.menu import BTN_MY_QUIZZES
from bot.keyboards.inline.quiz_inline import (
    MyQuizCallback,
    MyQuizzesListCallback,
    QuizDeleteCallback,
    QuizExportCallback,
    get_delete_confirm_keyboard,
    get_my_quiz_card_keyboard,
    get_my_quizzes_keyboard,
)
from services.export_service import build_docx, build_xlsx, export_filename, get_exportable_quiz
from services.quiz_service import delete_quiz, get_quizzes_created_by
from services.user_service import get_or_create_user

logger = logging.getLogger(__name__)
router = Router(name=__name__)

_MAX_LISTED_QUIZZES = 30
_NOT_FOUND = "❌ Test topilmadi yoki sizga tegishli emas."


async def _render_list(user: User) -> tuple[str, InlineKeyboardMarkup | None]:
    quizzes = await get_quizzes_created_by(user.id)
    if not quizzes:
        return "📂 Sizda hali test yo'q. 📝 Test yaratish tugmasi orqali yarating.", None

    shown = quizzes[:_MAX_LISTED_QUIZZES]
    note = f"\n<i>Oxirgi {len(shown)} ta test ko'rsatildi.</i>" if len(quizzes) > len(shown) else ""
    return (
        f"📂 <b>Mening testlarim</b> ({len(quizzes)} ta)\n\n"
        f"Boshlash, ulashish, fayl olish yoki o'chirish uchun testni tanlang:{note}",
        get_my_quizzes_keyboard([(q.id, q.title) for q in shown]),
    )


async def _edit(callback: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        logger.debug("my_quizzes: xabarni tahrirlab bo'lmadi, yangisi yuboriladi")
        await callback.message.answer(text, reply_markup=markup)


@router.message(F.chat.type == "private", F.text == BTN_MY_QUIZZES)
async def show_my_quizzes(message: Message) -> None:
    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    if user is None:
        await message.answer("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
        return

    text, markup = await _render_list(user)
    await message.answer(text, reply_markup=markup)


@router.callback_query(MyQuizzesListCallback.filter())
async def back_to_list(callback: CallbackQuery) -> None:
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    if user is None:
        await callback.answer("❌ Xatolik yuz berdi.", show_alert=True)
        return

    text, markup = await _render_list(user)
    await _edit(callback, text, markup)
    await callback.answer()


@router.callback_query(MyQuizCallback.filter())
async def show_quiz_card(callback: CallbackQuery, callback_data: MyQuizCallback, bot: Bot) -> None:
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    result = await get_exportable_quiz(callback_data.quiz_id, user) if user else None
    if result is None:
        await callback.answer(_NOT_FOUND, show_alert=True)
        return

    quiz, questions = result
    me = await bot.me()
    await _edit(
        callback,
        f"📋 <b>{escape(quiz.title)}</b>\n"
        f"❓ {len(questions)} ta savol\n"
        f"⏱ Har bir savol uchun {quiz.time_per_question_sec} soniya\n\n"
        f"📤 <b>Ulashish</b> — istalgan chatga test kartasini yuboradi.\n"
        f"👥 <b>Guruhda boshlash</b> — guruhni tanlaysiz, test o'sha yerda boshlanadi.",
        get_my_quiz_card_keyboard(quiz.id, me.username),
    )
    await callback.answer()


@router.callback_query(QuizDeleteCallback.filter(~F.confirm))
async def ask_delete_confirmation(callback: CallbackQuery, callback_data: QuizDeleteCallback) -> None:
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    result = await get_exportable_quiz(callback_data.quiz_id, user) if user else None
    if result is None:
        await callback.answer(_NOT_FOUND, show_alert=True)
        return

    quiz, questions = result
    await _edit(
        callback,
        f"🗑 <b>{escape(quiz.title)}</b> testini o'chirasizmi?\n\n"
        f"❓ {len(questions)} ta savol o'chadi. Guruhlarga ulashilgani va rejalari ham bekor qilinadi.\n"
        f"⚠️ Bu amalni bot orqali qaytarib bo'lmaydi.",
        get_delete_confirm_keyboard(quiz.id),
    )
    await callback.answer()


@router.callback_query(QuizDeleteCallback.filter(F.confirm))
async def confirm_delete(callback: CallbackQuery, callback_data: QuizDeleteCallback) -> None:
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    if user is None or not await delete_quiz(callback_data.quiz_id, user):
        await callback.answer(_NOT_FOUND, show_alert=True)
        return

    text, markup = await _render_list(user)
    await _edit(callback, f"✅ Test o'chirildi.\n\n{text}", markup)
    await callback.answer("🗑 Test o'chirildi")


@router.callback_query(QuizExportCallback.filter(F.fmt.in_({"docx", "xlsx"})))
async def send_quiz_file(callback: CallbackQuery, callback_data: QuizExportCallback) -> None:
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    result = await get_exportable_quiz(callback_data.quiz_id, user) if user else None
    if result is None:
        await callback.answer(_NOT_FOUND, show_alert=True)
        return

    quiz, questions = result
    if not questions:
        await callback.answer("❌ Bu testda savollar yo'q.", show_alert=True)
        return

    await callback.answer("⏳ Fayl tayyorlanmoqda...")
    if callback_data.fmt == "docx":
        content = await asyncio.to_thread(build_docx, quiz, questions)
        caption = f"📄 {quiz.title} — {len(questions)} ta savol. Har savolda 1-javob to'g'ri javob."
    else:
        content = await asyncio.to_thread(build_xlsx, questions)
        caption = f"📊 {quiz.title} — {len(questions)} ta savol. Tahrirlab, /import orqali qayta yuklash mumkin."

    await callback.message.answer_document(
        BufferedInputFile(content, filename=export_filename(quiz, callback_data.fmt)),
        caption=caption,
    )
