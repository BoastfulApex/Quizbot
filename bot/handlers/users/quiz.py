import asyncio
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputPollOption, Message, PollAnswer

from bot.keyboards.default.menu import BTN_MY_QUIZZES, BTN_START_TEST
from bot.keyboards.inline.quiz_inline import (
    QuizReadyCallback,
    QuizRetryCallback,
    QuizSelectCallback,
    get_quiz_list_keyboard,
    get_ready_keyboard,
    get_result_keyboard,
)
from bot.states.quiz_states import QuizReadyStates, QuizSelectStates
from bot.utils.quiz_runs import QuizRun, get_run, iter_runs, pop_run, register_run
from bot.utils.texts import GUIDE_MY_QUIZZES
from services.quiz_service import (
    find_quiz_by_name_or_id,
    finish_session,
    get_group_shared_quizzes,
    get_questions_for_quiz,
    get_quiz_by_id,
    get_session_ranking,
    get_session_stats,
    get_user_and_public_quizzes,
    start_quiz_session,
    submit_answer,
)
from services.user_service import get_or_create_user, is_admin_role

logger = logging.getLogger(__name__)
router = Router(name="quiz")

_OPTION_LETTERS = ("A", "B", "C", "D")
POLL_CLOSE_GRACE_SEC = 2
_bot_username: str | None = None


async def _get_bot_username(bot) -> str:
    global _bot_username
    if _bot_username is None:
        me = await bot.get_me()
        _bot_username = me.username
    return _bot_username


def _format_duration(seconds: int) -> str:
    minutes, secs = divmod(seconds, 60)
    if minutes == 0:
        return f"{secs} soniya"
    return f"{minutes} daqiqa {secs} soniya"


async def _route_start_test(message: Message, args: str | None, state: FSMContext) -> None:
    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    if user is None:
        await message.answer("Xatolik yuz berdi. Qayta urinib ko'ring.")
        return

    if message.chat.type == "private":
        await _handle_private_start(message, user, args, state)
    else:
        await _handle_group_start(message, user, state)


async def _handle_private_start(message: Message, user, query: str | None, state: FSMContext) -> None:
    if query:
        matches = await find_quiz_by_name_or_id(query.strip(), user.id)
        if len(matches) == 1:
            await _show_ready_card(message, message.from_user.id, matches[0].id, message.chat.id, state)
            return
        if len(matches) > 1:
            await state.set_state(QuizSelectStates.choosing_quiz)
            await message.answer(
                "Bir nechta moslik topildi, birini tanlang:",
                reply_markup=get_quiz_list_keyboard([(q.id, q.title) for q in matches]),
            )
            return
        await message.answer("❌ Mos test topilmadi.")
        return

    quizzes = await get_user_and_public_quizzes(user.id)
    if not quizzes:
        await message.answer("Hozircha testlar mavjud emas. /newquiz orqali birinchi testingizni yarating.")
        return
    await state.set_state(QuizSelectStates.choosing_quiz)
    await message.answer(
        "Boshlash uchun testni tanlang:",
        reply_markup=get_quiz_list_keyboard([(q.id, q.title) for q in quizzes]),
    )


async def _handle_group_start(message: Message, user, state: FSMContext) -> None:
    shared = await get_group_shared_quizzes(message.chat.id)
    if not shared:
        await message.answer("Bu guruhda test ulashilmagan. Shaxsiy chatda test tanlang yoki ulashing.")
        return
    if len(shared) == 1:
        await _show_ready_card(message, message.from_user.id, shared[0].id, message.chat.id, state)
        return
    await state.set_state(QuizSelectStates.choosing_quiz)
    await message.answer(
        "Qaysi testni boshlaymiz?",
        reply_markup=get_quiz_list_keyboard([(q.id, q.title) for q in shared]),
    )


@router.message(Command("startTest"))
async def cmd_start_test(message: Message, command: CommandObject, state: FSMContext) -> None:
    await _route_start_test(message, command.args, state)


@router.message(F.text == BTN_START_TEST, StateFilter(None))
async def guide_start_test_button(message: Message, state: FSMContext) -> None:
    await _route_start_test(message, None, state)


@router.message(F.text == BTN_MY_QUIZZES)
async def guide_my_quizzes(message: Message) -> None:
    await message.answer(GUIDE_MY_QUIZZES)


@router.callback_query(QuizSelectCallback.filter(), QuizSelectStates.choosing_quiz)
async def process_quiz_select(callback: CallbackQuery, callback_data: QuizSelectCallback, state: FSMContext) -> None:
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    if user is None:
        await callback.answer("Xatolik yuz berdi.", show_alert=True)
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await _show_ready_card(
        callback.message, callback.from_user.id, callback_data.quiz_id, callback.message.chat.id, state
    )
    await callback.answer()


async def launch_quiz_from_deep_link(message: Message, quiz_id: int, state: FSMContext) -> None:
    await _show_ready_card(message, message.from_user.id, quiz_id, message.chat.id, state)


async def _show_ready_card(
    message: Message, initiator_telegram_id: int, quiz_id: int, chat_id: int, state: FSMContext
) -> None:
    if get_run(chat_id) is not None:
        await message.answer("⚠️ Bu chatda hozir test ketyapti. Avval /stop bilan tugating.")
        return

    quiz = await get_quiz_by_id(quiz_id)
    if quiz is None:
        await message.answer("❌ Test topilmadi yoki faol emas.")
        return

    questions = await get_questions_for_quiz(quiz_id)
    if not questions:
        await message.answer("❌ Bu testda savollar yo'q.")
        return

    await state.set_state(QuizReadyStates.confirming)
    await state.update_data(quiz_id=quiz_id, chat_id=chat_id, initiator_telegram_id=initiator_telegram_id)
    await message.answer(
        f"📋 <b>{quiz.title}</b>\n\n"
        f"❓ {len(questions)} ta savol\n"
        f"⏱ Har bir savol uchun {quiz.time_per_question_sec} soniya\n"
        f"👁 Ovozlar ko'rinadigan bo'ladi\n\n"
        f"Tayyor bo'lganingizda tugmani bosing.\n"
        f"❌ Bekor qilish uchun /stop yuboring.",
        reply_markup=get_ready_keyboard(quiz_id),
    )


@router.callback_query(QuizReadyCallback.filter(), QuizReadyStates.confirming)
async def process_ready(callback: CallbackQuery, callback_data: QuizReadyCallback, state: FSMContext, bot) -> None:
    data = await state.get_data()
    if callback.from_user.id != data.get("initiator_telegram_id") or callback_data.quiz_id != data.get("quiz_id"):
        await callback.answer("❌ Bu tugma sizga tegishli emas yoki eskirgan.", show_alert=True)
        return

    chat_id = data["chat_id"]
    if get_run(chat_id) is not None:
        await callback.answer("⚠️ Bu chatda test allaqachon boshlangan.", show_alert=True)
        return

    quiz = await get_quiz_by_id(callback_data.quiz_id)
    questions = await get_questions_for_quiz(callback_data.quiz_id)
    if quiz is None or not questions:
        await callback.message.edit_text("❌ Test endi mavjud emas.")
        await state.clear()
        await callback.answer()
        return

    await callback.message.edit_text("⏳ SOZLANMOQDA...")
    await callback.answer()
    await state.clear()

    run = QuizRun(
        chat_id=chat_id,
        quiz_id=quiz.id,
        quiz_title=quiz.title,
        initiator_telegram_id=callback.from_user.id,
        time_per_question_sec=quiz.time_per_question_sec,
        total_questions=len(questions),
    )
    register_run(run)
    run.task = asyncio.create_task(_run_quiz(run, questions, bot))


async def _run_quiz(run: QuizRun, questions: list, bot) -> None:
    try:
        for question in questions:
            if run.stopped:
                return

            options = [
                InputPollOption(text=getattr(question, f"option_{letter.lower()}"))
                for letter in _OPTION_LETTERS
            ]
            correct_index = _OPTION_LETTERS.index(question.correct_option)

            try:
                sent = await bot.send_poll(
                    chat_id=run.chat_id,
                    question=f"[{run.current_index + 1}/{run.total_questions}] {question.question_text}",
                    options=options,
                    type="quiz",
                    is_anonymous=False,
                    correct_option_id=correct_index,
                    explanation=question.explanation or None,
                    open_period=run.time_per_question_sec,
                )
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
                continue
            except TelegramForbiddenError:
                logger.exception("send_poll: bot chatdan chiqarilgan, chat_id=%s", run.chat_id)
                return
            except TelegramBadRequest:
                logger.exception("send_poll xato: chat_id=%s, question_id=%s", run.chat_id, question.id)
                run.current_index += 1
                continue

            run.poll_id_to_question_id[sent.poll.id] = question.id
            run.current_index += 1
            await asyncio.sleep(run.time_per_question_sec + POLL_CLOSE_GRACE_SEC)
    except asyncio.CancelledError:
        raise
    finally:
        if pop_run(run.chat_id) is not None:
            await _finish_run(run, bot)


@router.poll_answer()
async def on_poll_answer(poll_answer: PollAnswer, bot) -> None:
    if poll_answer.user is None or not poll_answer.option_ids:
        return

    target_run = next((r for r in iter_runs() if poll_answer.poll_id in r.poll_id_to_question_id), None)
    if target_run is None:
        logger.debug("poll_answer: tegishli run topilmadi, poll_id=%s", poll_answer.poll_id)
        return

    question_id = target_run.poll_id_to_question_id[poll_answer.poll_id]
    db_user = await get_or_create_user(poll_answer.user.id, poll_answer.user.username)
    if db_user is None:
        return

    if poll_answer.user.id not in target_run.participants:
        session = await start_quiz_session(target_run.quiz_id, db_user.id, target_run.chat_id)
        if session is None:
            return
        display_name = poll_answer.user.username or poll_answer.user.first_name or str(poll_answer.user.id)
        target_run.participants[poll_answer.user.id] = (session.id, display_name)

    session_id, _ = target_run.participants[poll_answer.user.id]
    selected_letter = _OPTION_LETTERS[poll_answer.option_ids[0]]
    await submit_answer(session_id, question_id, selected_letter, None)


async def _finish_run(run: QuizRun, bot) -> None:
    session_ids = []
    for session_id, display_name in run.participants.values():
        await finish_session(session_id)
        session_ids.append((session_id, display_name))

    if not session_ids:
        await bot.send_message(run.chat_id, f"🏁 '{run.quiz_title}' test yakunlandi. Hech kim ovoz bermadi.")
        return

    if len(session_ids) == 1:
        session_id, _ = session_ids[0]
        await _send_single_result(run, session_id, bot)
        return

    results = []
    for session_id, display_name in session_ids:
        stats = await get_session_stats(session_id)
        if stats is not None:
            results.append((display_name, stats["score"], stats["total_questions"]))

    results.sort(key=lambda r: r[1], reverse=True)
    lines = [f"{i}. {name} — {score} ball" for i, (name, score, _) in enumerate(results, start=1)]
    await bot.send_message(run.chat_id, f"🏁 '{run.quiz_title}' test yakunlandi!\n\n" + "\n".join(lines))


async def _send_single_result(run: QuizRun, session_id: int, bot) -> None:
    stats = await get_session_stats(session_id)
    ranking = await get_session_ranking(session_id)
    if stats is None or ranking is None:
        await bot.send_message(run.chat_id, f"🏁 '{run.quiz_title}' test yakunlandi.")
        return

    duration_text = _format_duration(stats["duration_sec"] or 0)
    if ranking["percent_better"] is not None:
        rank_line = (
            f"{ranking['total']} dan {ranking['rank']}-o'rin. Siz ushbu testda ishtirok etgan "
            f"{ranking['percent_better']}% odamlardan yuqoriroq ball to'pladingiz."
        )
    else:
        rank_line = "Siz ushbu testda birinchi bo'lib qatnashdingiz!"

    text = (
        f"🎯 \"{run.quiz_title}\" testi yakunlandi!\n\n"
        f"Siz {stats['total_questions']} ta savolga javob berdingiz:\n\n"
        f"✅ To'g'ri – {stats['correct']}\n"
        f"❌ Xato – {stats['wrong']}\n"
        f"🏳 Tashlab ketilgan – {stats['skipped']}\n"
        f"⏱ {duration_text}\n\n"
        f"{rank_line}\n\n"
        f"Bu testda yana qatnashishingiz mumkin, lekin bu yetakchilardagi o'rningizni o'zgartirmaydi."
    )
    bot_username = await _get_bot_username(bot)
    await bot.send_message(run.chat_id, text, reply_markup=get_result_keyboard(run.quiz_id, bot_username))


@router.message(Command("stop"))
async def cmd_stop(message: Message, state: FSMContext, bot) -> None:
    current_state = await state.get_state()
    if current_state == QuizReadyStates.confirming.state:
        await state.clear()
        await message.answer("❌ Bekor qilindi.")
        return

    run = get_run(message.chat.id)
    if run is None:
        await message.answer("Bu yerda hozir faol test yo'q.")
        return

    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    is_owner = message.from_user.id == run.initiator_telegram_id
    is_admin = user is not None and is_admin_role(user)
    if not (is_owner or is_admin):
        await message.answer("❌ Faqat testni boshlagan foydalanuvchi yoki admin to'xtata oladi.")
        return

    stopped_run = pop_run(message.chat.id)
    if stopped_run is None:
        await message.answer("Test allaqachon tugagan.")
        return

    stopped_run.stopped = True
    if stopped_run.task is not None and not stopped_run.task.done():
        stopped_run.task.cancel()

    await message.answer("🛑 Test to'xtatildi.")
    await _finish_run(stopped_run, bot)


@router.callback_query(QuizRetryCallback.filter())
async def process_retry(callback: CallbackQuery, callback_data: QuizRetryCallback, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await _show_ready_card(
        callback.message, callback.from_user.id, callback_data.quiz_id, callback.message.chat.id, state
    )
