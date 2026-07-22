import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.inline.quiz_inline import VisibilityCallback, get_visibility_keyboard
from bot.states.ai_generate_states import AiGenerateStates
from bot.utils.limits import MAX_TIME_PER_QUESTION_SEC, MAX_TITLE_LEN, MIN_TIME_PER_QUESTION_SEC
from apps.quizzes.models import Quiz
from services.ai_generator_service import create_ai_log, generate_questions
from services.import_service import bulk_create_questions
from services.quiz_service import create_quiz
from services.user_service import get_or_create_user

logger = logging.getLogger(__name__)

router = Router(name="ai_generate")

_MIN_COUNT = 5
_MAX_COUNT = 20


@router.message(Command("generate"), StateFilter(None))
async def cmd_generate(message: Message, state: FSMContext) -> None:
    if message.chat.type != "private":
        await message.answer("⚠️ /generate buyrug'i faqat shaxsiy chatda ishlaydi.")
        return
    await state.set_state(AiGenerateStates.topic)
    await message.answer(
        "🤖 <b>AI savol generatsiyasi</b>\n\n"
        "Qaysi mavzu bo'yicha savollar yaratilsin?\n"
        "(masalan: Matematika, O'zbekiston tarixi, Python dasturlash)\n\n"
        "/cancel — bekor qilish",
        parse_mode="HTML",
    )


@router.message(Command("cancel"), StateFilter(AiGenerateStates))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Generatsiya bekor qilindi.")


@router.message(AiGenerateStates.topic)
async def process_topic(message: Message, state: FSMContext) -> None:
    topic = (message.text or "").strip()
    if not (3 <= len(topic) <= MAX_TITLE_LEN):
        await message.answer(f"⚠️ Mavzu 3-{MAX_TITLE_LEN} belgi orasida bo'lishi kerak. Qayta kiriting:")
        return
    await state.update_data(topic=topic)
    await state.set_state(AiGenerateStates.question_count)
    await message.answer(
        f"Nechta savol yaratilsin? ({_MIN_COUNT}-{_MAX_COUNT} oralig'ida son kiriting):"
    )


@router.message(AiGenerateStates.question_count)
async def process_question_count(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or not (_MIN_COUNT <= int(text) <= _MAX_COUNT):
        await message.answer(
            f"⚠️ {_MIN_COUNT} dan {_MAX_COUNT} gacha bo'lgan butun son kiriting:"
        )
        return
    await state.update_data(question_count=int(text))
    await state.set_state(AiGenerateStates.visibility)
    await message.answer("Test ko'rinishini tanlang:", reply_markup=get_visibility_keyboard())


@router.message(AiGenerateStates.visibility)
async def prompt_visibility_fallback(message: Message) -> None:
    await message.answer("Iltimos, quyidagi tugmalardan birini tanlang:", reply_markup=get_visibility_keyboard())


@router.callback_query(VisibilityCallback.filter(), AiGenerateStates.visibility)
async def process_visibility(callback: CallbackQuery, callback_data: VisibilityCallback, state: FSMContext) -> None:
    await state.update_data(visibility=callback_data.value)
    await state.set_state(AiGenerateStates.time_per_question)
    await callback.message.edit_text(
        f"⏱ Har bir savol uchun necha soniya beriladi? "
        f"({MIN_TIME_PER_QUESTION_SEC}-{MAX_TIME_PER_QUESTION_SEC} oralig'ida son kiriting):"
    )
    await callback.answer()


@router.message(AiGenerateStates.time_per_question)
async def process_time_and_generate(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or not (MIN_TIME_PER_QUESTION_SEC <= int(text) <= MAX_TIME_PER_QUESTION_SEC):
        await message.answer(
            f"⚠️ {MIN_TIME_PER_QUESTION_SEC} dan {MAX_TIME_PER_QUESTION_SEC} gacha bo'lgan butun son kiriting:"
        )
        return

    time_per_question = int(text)
    data = await state.get_data()
    topic: str = data["topic"]
    count: int = data["question_count"]
    visibility: str = data["visibility"]

    status_msg = await message.answer("⏳ Savollar yaratilmoqda, biroz kuting...")

    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    if user is None:
        await status_msg.edit_text("❌ Foydalanuvchi ma'lumotlarini olishda xatolik yuz berdi.")
        await state.clear()
        return

    try:
        questions = await generate_questions(topic=topic, count=count)
    except Exception:
        logger.exception("generate_questions xato: user_id=%s, topic=%s", user.id, topic)
        await status_msg.edit_text(
            "❌ AI bilan bog'lanishda xatolik yuz berdi. Keyinroq urinib ko'ring."
        )
        await state.clear()
        return

    if not questions:
        await status_msg.edit_text(
            "❌ AI savollarni yarata olmadi. Boshqa mavzu bilan urinib ko'ring."
        )
        await state.clear()
        return

    quiz = await create_quiz(
        created_by=user,
        title=topic,
        visibility=visibility,
        time_per_question_sec=time_per_question,
        source=Quiz.Source.AI,
    )
    if quiz is None:
        await status_msg.edit_text("❌ Test yaratishda xatolik yuz berdi. Qayta urinib ko'ring.")
        await state.clear()
        return

    created_count = await bulk_create_questions(quiz.id, questions)
    await create_ai_log(
        user_id=user.id,
        topic=topic,
        questions_count=created_count,
    )

    visibility_label = "🌐 Ommaviy" if visibility == Quiz.Visibility.PUBLIC else "🔒 Shaxsiy"
    await status_msg.edit_text(
        f"✅ <b>Generatsiya yakunlandi!</b>\n\n"
        f"📚 Mavzu: {topic}\n"
        f"❓ Yaratilgan savollar: {created_count} ta\n"
        f"👁 Ko'rinish: {visibility_label}\n"
        f"⏱ Har bir savol: {time_per_question} soniya\n\n"
        f"Test ID: <code>{quiz.id}</code>\n"
        f"/startTest orqali sinab ko'rishingiz mumkin.",
        parse_mode="HTML",
    )
    await state.clear()
