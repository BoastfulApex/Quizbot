import logging
from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.inline.quiz_inline import VisibilityCallback, get_visibility_keyboard
from bot.states.ai_generate_states import AiGenerateStates
from bot.utils.file_reader import SUPPORTED_EXTENSIONS, extract_text
from bot.utils.limits import MAX_TIME_PER_QUESTION_SEC, MAX_TITLE_LEN, MIN_TIME_PER_QUESTION_SEC
from apps.quizzes.models import Quiz
from services.ai_generator_service import generate_questions, create_ai_log
from services.import_service import bulk_create_questions
from services.quiz_service import create_quiz
from services.user_service import get_or_create_user

logger = logging.getLogger(__name__)

router = Router(name="ai_generate")

_MIN_COUNT = 5
_MAX_COUNT = 20
_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
_MAX_MATERIAL_CHARS = 12_000


@router.message(Command("generate"), StateFilter(None))
async def cmd_generate(message: Message, state: FSMContext) -> None:
    if message.chat.type != "private":
        await message.answer("⚠️ /generate buyrug'i faqat shaxsiy chatda ishlaydi.")
        return
    await state.set_state(AiGenerateStates.topic)
    ext_list = ", ".join(sorted(SUPPORTED_EXTENSIONS))
    await message.answer(
        "🤖 <b>AI savol generatsiyasi</b>\n\n"
        "Mavzuni ikki usulda kiritishingiz mumkin:\n\n"
        "✏️ <b>Mavzu nomi</b> — oddiy matn yozing\n"
        "(masalan: <i>Matematika</i>, <i>O'zbekiston tarixi</i>)\n\n"
        f"📄 <b>Hujjat fayli</b> — {ext_list} fayl yuboring\n"
        "(fayl mazmuniga asoslanib savollar yaratiladi)\n\n"
        "/cancel — bekor qilish",
        parse_mode="HTML",
    )


@router.message(Command("cancel"), StateFilter(AiGenerateStates))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Generatsiya bekor qilindi.")


@router.message(AiGenerateStates.topic, F.text)
async def process_topic_text(message: Message, state: FSMContext) -> None:
    topic = (message.text or "").strip()
    if not (3 <= len(topic) <= MAX_TITLE_LEN):
        await message.answer(f"⚠️ Mavzu nomi 3-{MAX_TITLE_LEN} belgi orasida bo'lishi kerak. Qayta kiriting:")
        return
    await state.update_data(topic=topic, material=None)
    await state.set_state(AiGenerateStates.question_count)
    await message.answer(
        f"Nechta savol yaratilsin? ({_MIN_COUNT}-{_MAX_COUNT} oralig'ida son kiriting):"
    )


@router.message(AiGenerateStates.topic, F.document)
async def process_topic_file(message: Message, state: FSMContext, bot: Bot) -> None:
    doc = message.document
    filename = doc.file_name or ""
    ext = ("." + filename.rsplit(".", 1)[-1]).lower() if "." in filename else ""

    if ext not in SUPPORTED_EXTENSIONS:
        ext_list = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        await message.answer(
            f"⚠️ Faqat {ext_list} fayl qabul qilinadi.",
            parse_mode="HTML",
        )
        return

    if doc.file_size and doc.file_size > _MAX_FILE_SIZE:
        await message.answer("⚠️ Fayl hajmi 5 MB dan oshmasligi kerak.")
        return

    buf = BytesIO()
    await bot.download(doc, destination=buf)
    buf.seek(0)

    try:
        content = extract_text(buf, filename)
    except ValueError as e:
        await message.answer(f"⚠️ {e}")
        return

    if len(content) < 50:
        await message.answer("⚠️ Fayl juda qisqa. Kamida 50 belgilik matn bo'lishi kerak.")
        return

    title = filename.rsplit(".", 1)[0][:MAX_TITLE_LEN] or "Fayl asosidagi test"
    await state.update_data(topic=title, material=content[:_MAX_MATERIAL_CHARS])
    await state.set_state(AiGenerateStates.question_count)

    chars = min(len(content), _MAX_MATERIAL_CHARS)
    await message.answer(
        f"✅ Fayl qabul qilindi: <b>{filename}</b> ({chars} belgi o'qildi)\n\n"
        f"Nechta savol yaratilsin? ({_MIN_COUNT}-{_MAX_COUNT} oralig'ida son kiriting):",
        parse_mode="HTML",
    )


@router.message(AiGenerateStates.topic)
async def process_topic_fallback(message: Message) -> None:
    await message.answer(
        "⚠️ Mavzu nomi (matn) yoki .txt fayl yuboring.\n/cancel — bekor qilish"
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
    material: str | None = data.get("material")

    source_label = "📄 Fayl asosida" if material else f"✏️ Mavzu: {topic}"
    status_msg = await message.answer(
        f"⏳ Savollar yaratilmoqda...\n{source_label}"
    )

    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    if user is None:
        await status_msg.edit_text("❌ Foydalanuvchi ma'lumotlarini olishda xatolik yuz berdi.")
        await state.clear()
        return

    try:
        questions = await generate_questions(
            topic=topic,
            count=count,
            material=material,
        )
    except Exception:
        logger.exception("generate_questions xato: user_id=%s, topic=%s", user.id, topic)
        await status_msg.edit_text(
            "❌ AI bilan bog'lanishda xatolik yuz berdi. Keyinroq urinib ko'ring."
        )
        await state.clear()
        return

    if not questions:
        await status_msg.edit_text(
            "❌ AI savollarni yarata olmadi. Boshqa mavzu yoki fayl bilan urinib ko'ring."
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
    await create_ai_log(user_id=user.id, topic=topic, questions_count=created_count)

    visibility_label = "🌐 Ommaviy" if visibility == Quiz.Visibility.PUBLIC else "🔒 Shaxsiy"
    mode_label = "📄 Fayl mazmunidan" if material else "✏️ Mavzu nomidan"
    await status_msg.edit_text(
        f"✅ <b>Generatsiya yakunlandi!</b>\n\n"
        f"📚 Test: {topic}\n"
        f"🔢 Yaratilgan savollar: {created_count} ta\n"
        f"🧠 Manba: {mode_label}\n"
        f"👁 Ko'rinish: {visibility_label}\n"
        f"⏱ Har bir savol: {time_per_question} soniya\n\n"
        f"Test ID: <code>{quiz.id}</code>\n"
        f"/startTest orqali sinab ko'rishingiz mumkin.",
        parse_mode="HTML",
    )
    await state.clear()
