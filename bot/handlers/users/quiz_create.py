from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.default.menu import BTN_CREATE_QUIZ
from bot.keyboards.inline.quiz_inline import (
    QuizAddMoreCallback,
    VisibilityCallback,
    get_add_more_keyboard,
    get_visibility_keyboard,
)
from bot.states.quiz_states import QuizCreateStates
from bot.utils.limits import (
    MAX_CATEGORY_LEN,
    MAX_DESC_LEN,
    MAX_DIFFICULTY_LEN,
    MAX_EXPLANATION_LEN,
    MAX_OPTION_LEN,
    MAX_QUESTION_LEN,
    MAX_TIME_PER_QUESTION_SEC,
    MAX_TITLE_LEN,
    MIN_TIME_PER_QUESTION_SEC,
)
from bot.utils.texts import GUIDE_CREATE_QUIZ
from services.quiz_service import add_question, count_questions, create_quiz
from services.user_service import get_or_create_user

router = Router(name="quiz_create")


@router.message(F.text == BTN_CREATE_QUIZ, StateFilter(None))
async def guide_create_quiz(message: Message) -> None:
    await message.answer(GUIDE_CREATE_QUIZ)


@router.message(Command("newquiz"))
async def cmd_newquiz(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(QuizCreateStates.title)
    await message.answer("📝 Yangi test yaratamiz.\n\nAvval test sarlavhasini kiriting (3-255 belgi):")


@router.message(Command("cancel"), StateFilter(QuizCreateStates))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Test yaratish bekor qilindi.")


@router.message(QuizCreateStates.title)
async def process_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not (3 <= len(title) <= MAX_TITLE_LEN):
        await message.answer(f"⚠️ Sarlavha 3-{MAX_TITLE_LEN} belgi orasida bo'lishi kerak. Qayta kiriting:")
        return
    await state.update_data(title=title)
    await state.set_state(QuizCreateStates.description)
    await message.answer("Tavsif kiriting (yoki /skip):")


@router.message(QuizCreateStates.description)
async def process_description(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    description = "" if text.strip() == "/skip" else text.strip()
    if len(description) > MAX_DESC_LEN:
        await message.answer(f"⚠️ Tavsif {MAX_DESC_LEN} belgidan oshmasligi kerak. Qayta kiriting:")
        return
    await state.update_data(description=description)
    await state.set_state(QuizCreateStates.category)
    await message.answer("Kategoriya kiriting (yoki /skip):")


@router.message(QuizCreateStates.category)
async def process_category(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    category = "" if text.strip() == "/skip" else text.strip()
    if len(category) > MAX_CATEGORY_LEN:
        await message.answer(f"⚠️ Kategoriya {MAX_CATEGORY_LEN} belgidan oshmasligi kerak. Qayta kiriting:")
        return
    await state.update_data(category=category)
    await state.set_state(QuizCreateStates.difficulty)
    await message.answer("Qiyinlik darajasini kiriting (masalan: oson/o'rta/qiyin, yoki /skip):")


@router.message(QuizCreateStates.difficulty)
async def process_difficulty(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    difficulty = "" if text.strip() == "/skip" else text.strip()
    if len(difficulty) > MAX_DIFFICULTY_LEN:
        await message.answer(f"⚠️ Qiyinlik darajasi {MAX_DIFFICULTY_LEN} belgidan oshmasligi kerak. Qayta kiriting:")
        return
    await state.update_data(difficulty=difficulty)
    await state.set_state(QuizCreateStates.visibility)
    await message.answer("Test ko'rinishini tanlang:", reply_markup=get_visibility_keyboard())


@router.message(QuizCreateStates.visibility)
async def prompt_visibility_fallback(message: Message) -> None:
    await message.answer("Iltimos, quyidagi tugmalardan birini tanlang:", reply_markup=get_visibility_keyboard())


@router.callback_query(VisibilityCallback.filter(), QuizCreateStates.visibility)
async def process_visibility(callback: CallbackQuery, callback_data: VisibilityCallback, state: FSMContext) -> None:
    await state.update_data(visibility=callback_data.value)
    await state.set_state(QuizCreateStates.time_per_question)
    await callback.message.edit_text(
        f"⏱ Har bir savol uchun necha soniya beriladi? "
        f"({MIN_TIME_PER_QUESTION_SEC}-{MAX_TIME_PER_QUESTION_SEC} oralig'ida son kiriting):"
    )
    await callback.answer()


@router.message(QuizCreateStates.time_per_question)
async def process_time_per_question(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or not (MIN_TIME_PER_QUESTION_SEC <= int(text) <= MAX_TIME_PER_QUESTION_SEC):
        await message.answer(
            f"⚠️ {MIN_TIME_PER_QUESTION_SEC} dan {MAX_TIME_PER_QUESTION_SEC} gacha bo'lgan butun son kiriting:"
        )
        return

    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    if user is None:
        await message.answer("Xatolik yuz berdi.")
        return

    data = await state.get_data()
    quiz = await create_quiz(
        created_by=user,
        title=data["title"],
        description=data.get("description", ""),
        category=data.get("category", ""),
        difficulty=data.get("difficulty", ""),
        visibility=data["visibility"],
        time_per_question_sec=int(text),
    )
    if quiz is None:
        await message.answer("❌ Test yaratishda xatolik yuz berdi. Qayta urinib ko'ring.")
        await state.clear()
        return

    await state.update_data(quiz_id=quiz.id)
    await state.set_state(QuizCreateStates.question_text)
    await message.answer(f"✅ '{quiz.title}' yaratildi.\n\n1-savol matnini kiriting:")


@router.message(QuizCreateStates.question_text)
async def process_question_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not (1 <= len(text) <= MAX_QUESTION_LEN):
        await message.answer(f"⚠️ Savol matni bo'sh bo'lmasligi va {MAX_QUESTION_LEN} belgidan oshmasligi kerak:")
        return
    await state.update_data(question_text=text)
    await state.set_state(QuizCreateStates.question_option_a)
    await message.answer("A variantini kiriting:")


@router.message(QuizCreateStates.question_option_a)
async def process_option_a(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not (1 <= len(text) <= MAX_OPTION_LEN):
        await message.answer(f"⚠️ Variant bo'sh bo'lmasligi va {MAX_OPTION_LEN} belgidan oshmasligi kerak:")
        return
    await state.update_data(question_option_a=text)
    await state.set_state(QuizCreateStates.question_option_b)
    await message.answer("B variantini kiriting:")


@router.message(QuizCreateStates.question_option_b)
async def process_option_b(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not (1 <= len(text) <= MAX_OPTION_LEN):
        await message.answer(f"⚠️ Variant bo'sh bo'lmasligi va {MAX_OPTION_LEN} belgidan oshmasligi kerak:")
        return
    await state.update_data(question_option_b=text)
    await state.set_state(QuizCreateStates.question_option_c)
    await message.answer("C variantini kiriting:")


@router.message(QuizCreateStates.question_option_c)
async def process_option_c(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not (1 <= len(text) <= MAX_OPTION_LEN):
        await message.answer(f"⚠️ Variant bo'sh bo'lmasligi va {MAX_OPTION_LEN} belgidan oshmasligi kerak:")
        return
    await state.update_data(question_option_c=text)
    await state.set_state(QuizCreateStates.question_option_d)
    await message.answer("D variantini kiriting:")


@router.message(QuizCreateStates.question_option_d)
async def process_option_d(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not (1 <= len(text) <= MAX_OPTION_LEN):
        await message.answer(f"⚠️ Variant bo'sh bo'lmasligi va {MAX_OPTION_LEN} belgidan oshmasligi kerak:")
        return
    await state.update_data(question_option_d=text)
    await state.set_state(QuizCreateStates.question_correct)
    await message.answer("To'g'ri javobni kiriting (A, B, C yoki D):")


@router.message(QuizCreateStates.question_correct)
async def process_correct_option(message: Message, state: FSMContext) -> None:
    option = (message.text or "").strip().upper()
    if option not in ("A", "B", "C", "D"):
        await message.answer("⚠️ Faqat A, B, C yoki D harflaridan birini kiriting:")
        return
    await state.update_data(question_correct=option)
    await state.set_state(QuizCreateStates.question_explanation)
    await message.answer("Izoh kiriting (yoki /skip):")


@router.message(QuizCreateStates.question_explanation)
async def process_explanation(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    explanation = "" if text.strip() == "/skip" else text.strip()
    if len(explanation) > MAX_EXPLANATION_LEN:
        await message.answer(f"⚠️ Izoh {MAX_EXPLANATION_LEN} belgidan oshmasligi kerak. Qayta kiriting:")
        return

    data = await state.get_data()
    question = await add_question(
        quiz_id=data["quiz_id"],
        question_text=data["question_text"],
        option_a=data["question_option_a"],
        option_b=data["question_option_b"],
        option_c=data["question_option_c"],
        option_d=data["question_option_d"],
        correct_option=data["question_correct"],
        explanation=explanation,
    )
    if question is None:
        await message.answer("❌ Savol saqlanmadi (xatolik). Qayta urinib ko'ring yoki /cancel bosing.")
        return

    total = await count_questions(data["quiz_id"])
    await state.set_state(QuizCreateStates.confirm_add_more)
    await message.answer(
        f"✅ Savol saqlandi. Jami: {total} ta savol.\n\nDavom etasizmi?",
        reply_markup=get_add_more_keyboard(),
    )


@router.callback_query(QuizAddMoreCallback.filter(), QuizCreateStates.confirm_add_more)
async def process_add_more(callback: CallbackQuery, callback_data: QuizAddMoreCallback, state: FSMContext) -> None:
    if callback_data.action == "add":
        await state.set_state(QuizCreateStates.question_text)
        await callback.message.edit_text("Keyingi savol matnini kiriting:")
        await callback.answer()
        return

    data = await state.get_data()
    total = await count_questions(data["quiz_id"])
    await callback.message.edit_text(
        f"🎉 Test yaratildi! Jami savollar soni: {total}.\n\nTestni /startTest orqali sinab ko'rishingiz mumkin."
    )
    await state.clear()
    await callback.answer()
