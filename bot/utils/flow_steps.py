"""Ko'p bosqichli oqimlar (FSM) uchun yagona qadamlar jadvali.

Har bir state uchun: oldingi state (``⬅️ Orqaga`` qayerga olib boradi) va shu qadamning
savol matni + klaviaturasi. Handlerlar keyingi qadamga ``ask()`` orqali o'tadi, navigatsiya
handleri esa ``⬅️ Orqaga`` bosilganda xuddi shu jadvaldan foydalanadi.
"""
import logging
from collections.abc import Callable
from dataclasses import dataclass

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import InlineKeyboardMarkup, Message

from bot.keyboards.inline.import_inline import get_import_target_keyboard
from bot.keyboards.inline.nav_inline import with_nav
from bot.keyboards.inline.quiz_inline import get_question_count_keyboard, get_visibility_keyboard
from bot.states.ai_generate_states import AiGenerateStates
from bot.states.import_states import ImportStates
from bot.states.quiz_states import QuizCreateStates, QuizReadyStates, QuizSelectStates
from bot.utils.file_reader import SUPPORTED_EXTENSIONS
from bot.utils.limits import MAX_TIME_PER_QUESTION_SEC, MAX_TITLE_LEN, MIN_TIME_PER_QUESTION_SEC

logger = logging.getLogger(__name__)

Render = Callable[[dict], tuple[str, InlineKeyboardMarkup | None]]

_TIME_PROMPT = (
    f"⏱ Har bir savol uchun necha soniya beriladi? "
    f"({MIN_TIME_PER_QUESTION_SEC}-{MAX_TIME_PER_QUESTION_SEC} oralig'ida son kiriting):"
)


def _text(value: str) -> Render:
    return lambda data: (value, None)


def _generate_intro(data: dict) -> tuple[str, None]:
    ext_list = ", ".join(sorted(SUPPORTED_EXTENSIONS))
    return (
        "🤖 <b>AI savol generatsiyasi</b>\n\n"
        "Mavzuni ikki usulda kiritishingiz mumkin:\n\n"
        "✏️ <b>Mavzu nomi</b> — oddiy matn yozing\n"
        "(masalan: <i>Matematika</i>, <i>O'zbekiston tarixi</i>)\n\n"
        f"📄 <b>Hujjat fayli</b> — {ext_list} fayl yuboring\n"
        "(fayl mazmuniga asoslanib savollar yaratiladi)",
        None,
    )


@dataclass(frozen=True)
class Step:
    prev: State | None
    render: Render | None = None


STEPS: dict[str, Step] = {
    # --- qo'lda test yaratish ---
    QuizCreateStates.title.state: Step(None, _text(
        f"📝 Yangi test yaratamiz.\n\nTest sarlavhasini kiriting (3-{MAX_TITLE_LEN} belgi):")),
    QuizCreateStates.description.state: Step(QuizCreateStates.title, _text("Tavsif kiriting (yoki /skip):")),
    QuizCreateStates.category.state: Step(QuizCreateStates.description, _text("Kategoriya kiriting (yoki /skip):")),
    QuizCreateStates.difficulty.state: Step(QuizCreateStates.category, _text(
        "Qiyinlik darajasini kiriting (masalan: oson/o'rta/qiyin, yoki /skip):")),
    QuizCreateStates.visibility.state: Step(QuizCreateStates.difficulty,
                                            lambda data: ("Test ko'rinishini tanlang:", get_visibility_keyboard())),
    QuizCreateStates.time_per_question.state: Step(QuizCreateStates.visibility, _text(_TIME_PROMPT)),
    # Test bazada yaratilgandan keyin sozlamalarga qaytib bo'lmaydi — faqat bekor qilish.
    QuizCreateStates.question_text.state: Step(
        None, lambda data: (f"{data.get('question_no', 1)}-savol matnini kiriting:", None)),
    QuizCreateStates.question_option_a.state: Step(QuizCreateStates.question_text, _text("A variantini kiriting:")),
    QuizCreateStates.question_option_b.state: Step(QuizCreateStates.question_option_a, _text("B variantini kiriting:")),
    QuizCreateStates.question_option_c.state: Step(QuizCreateStates.question_option_b, _text("C variantini kiriting:")),
    QuizCreateStates.question_option_d.state: Step(QuizCreateStates.question_option_c, _text("D variantini kiriting:")),
    QuizCreateStates.question_correct.state: Step(QuizCreateStates.question_option_d, _text(
        "To'g'ri javobni kiriting (A, B, C yoki D):")),
    QuizCreateStates.question_explanation.state: Step(QuizCreateStates.question_correct, _text(
        "Izoh kiriting (yoki /skip):")),
    QuizCreateStates.confirm_add_more.state: Step(None),

    # --- AI generatsiya ---
    AiGenerateStates.topic.state: Step(None, _generate_intro),
    AiGenerateStates.question_count.state: Step(
        AiGenerateStates.topic, lambda data: ("Nechta savol yaratilsin?", get_question_count_keyboard())),
    AiGenerateStates.visibility.state: Step(
        AiGenerateStates.question_count, lambda data: ("Test ko'rinishini tanlang:", get_visibility_keyboard())),
    AiGenerateStates.time_per_question.state: Step(AiGenerateStates.visibility, _text(_TIME_PROMPT)),

    # --- import ---
    ImportStates.choosing_target.state: Step(None, lambda data: (
        "📥 <b>Testga savollarni import qilish</b>\n\n"
        "Savollarni yangi testga yoki mavjud testga qo'shasizmi?",
        get_import_target_keyboard(),
    )),
    ImportStates.new_quiz_title.state: Step(ImportStates.choosing_target, _text(
        f"📝 Yangi test sarlavhasini kiriting (3-{MAX_TITLE_LEN} belgi):")),
    ImportStates.new_quiz_time_per_question.state: Step(ImportStates.new_quiz_title, _text(_TIME_PROMPT)),
    ImportStates.new_quiz_visibility.state: Step(
        ImportStates.new_quiz_time_per_question,
        lambda data: ("Test ko'rinishini tanlang:", get_visibility_keyboard())),
    ImportStates.choosing_existing_quiz.state: Step(ImportStates.choosing_target),
    ImportStates.awaiting_file.state: Step(None),

    # --- test tanlash / boshlash ---
    QuizSelectStates.choosing_quiz.state: Step(None),
    QuizReadyStates.confirming.state: Step(None),
}


def nav_for(state: State, markup: InlineKeyboardMarkup | None = None) -> InlineKeyboardMarkup:
    """Shu qadam uchun klaviatura + ``Orqaga``/``Bekor qilish`` qatori."""
    step = STEPS.get(state.state)
    return with_nav(markup, back=bool(step and step.prev))


async def ask(message: Message, state: FSMContext, new_state: State, *, edit: bool = False) -> None:
    """State'ni o'rnatadi va shu qadamning savolini navigatsiya tugmalari bilan yuboradi."""
    await state.set_state(new_state)
    data = await state.get_data()
    text, markup = STEPS[new_state.state].render(data)
    reply_markup = nav_for(new_state, markup)
    if edit:
        try:
            await message.edit_text(text, reply_markup=reply_markup)
            return
        except TelegramBadRequest:
            # Xabar matnsiz (masalan, hujjat) yoki o'zgarmagan — yangisini yuboramiz.
            logger.debug("ask: xabarni tahrirlab bo'lmadi, yangisi yuboriladi (state=%s)", new_state.state)
    await message.answer(text, reply_markup=reply_markup)
