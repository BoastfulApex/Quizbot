import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.keyboards.default.menu import BTN_MY_QUIZZES
from bot.keyboards.inline.quiz_inline import (
    MyQuizCallback,
    QuizExportCallback,
    get_my_quiz_card_keyboard,
    get_my_quizzes_keyboard,
)
from services.export_service import build_docx, build_xlsx, export_filename, get_exportable_quiz
from services.quiz_service import get_quizzes_created_by
from services.user_service import get_or_create_user

logger = logging.getLogger(__name__)
router = Router(name=__name__)

_MAX_LISTED_QUIZZES = 30


@router.message(F.chat.type == "private", F.text == BTN_MY_QUIZZES)
async def show_my_quizzes(message: Message) -> None:
    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    if user is None:
        await message.answer("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
        return

    quizzes = await get_quizzes_created_by(user.id)
    if not quizzes:
        await message.answer("Sizda hali test yo'q. /newquiz yoki /generate orqali yarating.")
        return

    shown = quizzes[:_MAX_LISTED_QUIZZES]
    note = f"\n<i>Oxirgi {len(shown)} ta test ko'rsatildi.</i>" if len(quizzes) > len(shown) else ""
    await message.answer(
        f"📂 <b>Mening testlarim</b>\n\nBoshlash, ulashish yoki fayl olish uchun testni tanlang:{note}",
        parse_mode="HTML",
        reply_markup=get_my_quizzes_keyboard([(q.id, q.title) for q in shown]),
    )


@router.callback_query(MyQuizCallback.filter())
async def show_quiz_card(callback: CallbackQuery, callback_data: MyQuizCallback, bot: Bot) -> None:
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    result = await get_exportable_quiz(callback_data.quiz_id, user) if user else None
    if result is None:
        await callback.answer("❌ Test topilmadi yoki sizga tegishli emas.", show_alert=True)
        return

    quiz, questions = result
    me = await bot.me()
    await callback.message.answer(
        f"📋 <b>{quiz.title}</b>\n"
        f"❓ {len(questions)} ta savol\n"
        f"⏱ Har bir savol uchun {quiz.time_per_question_sec} soniya\n\n"
        f"📤 <b>Ulashish</b> — istalgan chatga test kartasini yuboradi.\n"
        f"👥 <b>Guruhda boshlash</b> — guruhni tanlaysiz, test o'sha yerda boshlanadi.",
        parse_mode="HTML",
        reply_markup=get_my_quiz_card_keyboard(quiz.id, me.username),
    )
    await callback.answer()


@router.callback_query(QuizExportCallback.filter(F.fmt.in_({"docx", "xlsx"})))
async def send_quiz_file(callback: CallbackQuery, callback_data: QuizExportCallback) -> None:
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    result = await get_exportable_quiz(callback_data.quiz_id, user) if user else None
    if result is None:
        await callback.answer("❌ Test topilmadi yoki sizga tegishli emas.", show_alert=True)
        return

    quiz, questions = result
    if not questions:
        await callback.answer("❌ Bu testda savollar yo'q.", show_alert=True)
        return

    await callback.answer("⏳ Fayl tayyorlanmoqda...")
    if callback_data.fmt == "docx":
        content = await asyncio.to_thread(build_docx, quiz, questions)
        caption = f"📄 {quiz.title} — {len(questions)} ta savol, oxirida javoblar kaliti."
    else:
        content = await asyncio.to_thread(build_xlsx, questions)
        caption = f"📊 {quiz.title} — {len(questions)} ta savol. Tahrirlab, /import orqali qayta yuklash mumkin."

    await callback.message.answer_document(
        BufferedInputFile(content, filename=export_filename(quiz, callback_data.fmt)),
        caption=caption,
    )
