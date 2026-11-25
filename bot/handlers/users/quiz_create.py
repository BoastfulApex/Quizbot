from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.default.menu import BTN_CREATE_QUIZ
from bot.keyboards.inline.nav_inline import with_nav
from bot.keyboards.inline.quiz_inline import (
    CreateMethodCallback,
    QuizAddMoreCallback,
    VisibilityCallback,
    get_add_more_keyboard,
    get_create_method_keyboard,
    get_visibility_keyboard,
)
from bot.states.quiz_states import QuizCreateStates
from bot.utils.flow_steps import ask
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


@router.message(F.chat.type == "private", F.text == BTN_CREATE_QUIZ, StateFilter(None))
async def guide_create_quiz(message: Message) -> None:
    await message.answer(GUIDE_CREATE_QUIZ, reply_markup=get_create_method_keyboard())


@router.callback_query(CreateMethodCallback.filter())
async def choose_create_method(callback: CallbackQuery, callback_data: CreateMethodCallback, state: FSMContext) -> None:
    # Oqim boshlovchilari shu yerda import qilinadi — handler modullari orasida aylanma import bo'lmasin.
    from bot.handlers.users.ai_generate import start_generate_flow
    from bot.handlers.users.import_handler import start_import_flow

    await callback.answer()
    await state.clear()
    if callback_data.method == "manual":
        await ask(callback.message, state, QuizCreateStates.title, edit=True)
    elif callback_data.method == "import":
        await start_import_flow(callback.message, state, edit=True)
    else:
        await start_generate_flow(callback.message, state, edit=True)


@router.message(Command("newquiz"))
async def cmd_newquiz(message: Message, state: FSMContext) -> None:
    await state.clear()
    await ask(message, state, QuizCreateStates.title)


@router.message(Command("cancel"), StateFilter(QuizCreateStates))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    quiz_id = data.get("created_quiz_id")
    total = await count_questions(quiz_id) if quiz_id else 0
    if total:
        await message.answer(f"❌ Test yaratish to'xtatildi. Test {total} ta savol bilan saqlandi.")
    else:
        await message.answer("❌ Test yaratish bekor qilindi.")


@router.message(QuizCreateStates.title)
async def process_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not (3 <= len(title) <= MAX_TITLE_LEN):
        await message.answer(f"⚠️ Sarlavha 3-{MAX_TITLE_LEN} belgi orasida bo'lishi kerak. Qayta kiriting:")
        return
    await state.update_data(title=title)
    await ask(message, state, QuizCreateStates.description)


@router.message(QuizCreateStates.description)
async def process_description(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    description = "" if text.strip() == "/skip" else text.strip()
    if len(description) > MAX_DESC_LEN:
        await message.answer(f"⚠️ Tavsif {MAX_DESC_LEN} belgidan oshmasligi kerak. Qayta kiriting:")
        return
    await state.update_data(description=description)
    await ask(message, state, QuizCreateStates.category)


@router.message(QuizCreateStates.category)
async def process_category(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    category = "" if text.strip() == "/skip" else text.strip()
    if len(category) > MAX_CATEGORY_LEN:
        await message.answer(f"⚠️ Kategoriya {MAX_CATEGORY_LEN} belgidan oshmasligi kerak. Qayta kiriting:")
        return
    await state.update_data(category=category)
    await ask(message, state, QuizCreateStates.difficulty)


@router.message(QuizCreateStates.difficulty)
async def process_difficulty(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    difficulty = "" if text.strip() == "/skip" else text.strip()
    if len(difficulty) > MAX_DIFFICULTY_LEN:
        await message.answer(f"⚠️ Qiyinlik darajasi {MAX_DIFFICULTY_LEN} belgidan oshmasligi kerak. Qayta kiriting:")
        return
    await state.update_data(difficulty=difficulty)
    await ask(message, state, QuizCreateStates.visibility)


@router.message(QuizCreateStates.visibility)
async def prompt_visibility_fallback(message: Message) -> None:
    await message.answer("Iltimos, quyidagi tugmalardan birini tanlang:", reply_markup=with_nav(get_visibility_keyboard()))


@router.callback_query(VisibilityCallback.filter(), QuizCreateStates.visibility)
async def process_visibility(callback: CallbackQuery, callback_data: VisibilityCallback, state: FSMContext) -> None:
    await state.update_data(visibility=callback_data.value)
    await ask(callback.message, state, QuizCreateStates.time_per_question, edit=True)
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

    await state.update_data(quiz_id=quiz.id, created_quiz_id=quiz.id, question_no=1)
    await message.answer(f"✅ '{quiz.title}' yaratildi. Endi savollarni kiritamiz.")
    await ask(message, state, QuizCreateStates.question_text)


@router.message(QuizCreateStates.question_text)
async def process_question_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not (1 <= len(text) <= MAX_QUESTION_LEN):
        await message.answer(f"⚠️ Savol matni bo'sh bo'lmasligi va {MAX_QUESTION_LEN} belgidan oshmasligi kerak:")
        return
    await state.update_data(question_text=text)
    await ask(message, state, QuizCreateStates.question_option_a)


@router.message(QuizCreateStates.question_option_a)
async def process_option_a(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not (1 <= len(text) <= MAX_OPTION_LEN):
        await message.answer(f"⚠️ Variant bo'sh bo'lmasligi va {MAX_OPTION_LEN} belgidan oshmasligi kerak:")
        return
    await state.update_data(question_option_a=text)
    await ask(message, state, QuizCreateStates.question_option_b)


@router.message(QuizCreateStates.question_option_b)
async def process_option_b(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not (1 <= len(text) <= MAX_OPTION_LEN):
        await message.answer(f"⚠️ Variant bo'sh bo'lmasligi va {MAX_OPTION_LEN} belgidan oshmasligi kerak:")
        return
    await state.update_data(question_option_b=text)
    await ask(message, state, QuizCreateStates.question_option_c)


@router.message(QuizCreateStates.question_option_c)
async def process_option_c(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not (1 <= len(text) <= MAX_OPTION_LEN):
        await message.answer(f"⚠️ Variant bo'sh bo'lmasligi va {MAX_OPTION_LEN} belgidan oshmasligi kerak:")
        return
    await state.update_data(question_option_c=text)
    await ask(message, state, QuizCreateStates.question_option_d)


@router.message(QuizCreateStates.question_option_d)
async def process_option_d(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not (1 <= len(text) <= MAX_OPTION_LEN):
        await message.answer(f"⚠️ Variant bo'sh bo'lmasligi va {MAX_OPTION_LEN} belgidan oshmasligi kerak:")
        return
    await state.update_data(question_option_d=text)
    await ask(message, state, QuizCreateStates.question_correct)


@router.message(QuizCreateStates.question_correct)
async def process_correct_option(message: Message, state: FSMContext) -> None:
    option = (message.text or "").strip().upper()
    if option not in ("A", "B", "C", "D"):
        await message.answer("⚠️ Faqat A, B, C yoki D harflaridan birini kiriting:")
        return
    await state.update_data(question_correct=option)
    await ask(message, state, QuizCreateStates.question_explanation)


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
    await state.update_data(question_no=total + 1)
    await state.set_state(QuizCreateStates.confirm_add_more)
    await message.answer(
        f"✅ Savol saqlandi. Jami: {total} ta savol.\n\nDavom etasizmi?",
        reply_markup=get_add_more_keyboard(),
    )


@router.callback_query(QuizAddMoreCallback.filter(), QuizCreateStates.confirm_add_more)
async def process_add_more(callback: CallbackQuery, callback_data: QuizAddMoreCallback, state: FSMContext) -> None:
    if callback_data.action == "add":
        await ask(callback.message, state, QuizCreateStates.question_text, edit=True)
        await callback.answer()
        return

    data = await state.get_data()
    total = await count_questions(data["quiz_id"])
    await callback.message.edit_text(
        f"🎉 Test yaratildi! Jami savollar soni: {total}.\n\nTestni /starttest orqali sinab ko'rishingiz mumkin."
    )
    await state.clear()
    await callback.answer()
