import asyncio
import logging
import time
from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from apps.quizzes.models import Quiz
from bot.keyboards.inline.import_inline import ImportTargetCallback, get_import_target_keyboard
from bot.keyboards.inline.quiz_inline import (
    QuizSelectCallback,
    VisibilityCallback,
    get_quiz_list_keyboard,
    get_visibility_keyboard,
)
from bot.states.import_states import ImportStates
from bot.utils.limits import MAX_TIME_PER_QUESTION_SEC, MAX_TITLE_LEN, MIN_TIME_PER_QUESTION_SEC
from services.import_service import (
    bulk_create_questions,
    check_required_columns,
    count_imports_today,
    create_import_log,
    get_import_limits,
    read_dataframe,
    validate_rows,
)
from services.quiz_service import count_questions, create_quiz, get_quiz_by_id, get_quizzes_created_by
from services.user_service import get_or_create_user

logger = logging.getLogger(__name__)
router = Router(name="import")

_MAX_FILE_BYTES = 20 * 1024 * 1024
_PROGRESS_CHUNK = 200
_PROGRESS_MIN_INTERVAL = 2.0


@router.message(Command("import"))
async def cmd_import(message: Message, state: FSMContext) -> None:
    if message.chat.type != "private":
        await message.answer("⚠️ /import faqat shaxsiy chatda ishlaydi.")
        return
    await state.clear()
    await state.set_state(ImportStates.choosing_target)
    await message.answer(
        "📥 <b>Testga savollarni import qilish</b>\n\n"
        "Savollarni yangi testga yoki mavjud testga qo'shasizmi?",
        parse_mode="HTML",
        reply_markup=get_import_target_keyboard(),
    )


@router.message(Command("cancel"), StateFilter(ImportStates))
async def cmd_cancel_import(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Import bekor qilindi.")


@router.message(Command("done"), StateFilter(ImportStates.awaiting_file))
async def cmd_done_import(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    quiz_id = data.get("quiz_id")
    if quiz_id:
        total = await count_questions(quiz_id)
        await message.answer(f"✅ Import yakunlandi. Testda jami <b>{total}</b> ta savol.", parse_mode="HTML")
    else:
        await message.answer("✅ Import yakunlandi.")
    await state.clear()


# --- target tanlash ---

@router.callback_query(ImportTargetCallback.filter(), ImportStates.choosing_target)
async def process_import_target(callback: CallbackQuery, callback_data: ImportTargetCallback, state: FSMContext) -> None:
    await callback.answer()
    if callback_data.mode == "new":
        await state.set_state(ImportStates.new_quiz_title)
        await callback.message.edit_text(
            f"📝 Yangi test sarlavhasini kiriting (3-{MAX_TITLE_LEN} belgi):"
        )
    else:
        user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
        if user is None:
            await callback.message.edit_text("❌ Foydalanuvchi ma'lumotlari topilmadi.")
            await state.clear()
            return
        quizzes = await get_quizzes_created_by(user.id)
        if not quizzes:
            await callback.message.edit_text(
                "❌ Sizda hali test yo'q.\n\n/newquiz orqali yangi test yarating."
            )
            await state.clear()
            return
        pairs = [(q.id, q.title) for q in quizzes[:20]]
        await state.set_state(ImportStates.choosing_existing_quiz)
        await callback.message.edit_text(
            "📂 Qaysi testga savol qo'shmoqchisiz?",
            reply_markup=get_quiz_list_keyboard(pairs),
        )


# --- yangi test mini-oqimi ---

@router.message(ImportStates.new_quiz_title)
async def process_import_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not (3 <= len(title) <= MAX_TITLE_LEN):
        await message.answer(f"⚠️ Sarlavha 3-{MAX_TITLE_LEN} belgi orasida bo'lishi kerak. Qayta kiriting:")
        return
    await state.update_data(new_title=title)
    await state.set_state(ImportStates.new_quiz_time_per_question)
    await message.answer(
        f"⏱ Har bir savol uchun necha soniya? ({MIN_TIME_PER_QUESTION_SEC}-{MAX_TIME_PER_QUESTION_SEC}):"
    )


@router.message(ImportStates.new_quiz_time_per_question)
async def process_import_time(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or not (MIN_TIME_PER_QUESTION_SEC <= int(text) <= MAX_TIME_PER_QUESTION_SEC):
        await message.answer(
            f"⚠️ {MIN_TIME_PER_QUESTION_SEC}-{MAX_TIME_PER_QUESTION_SEC} oralig'ida son kiriting:"
        )
        return
    await state.update_data(new_time=int(text))
    await state.set_state(ImportStates.new_quiz_visibility)
    await message.answer("Test ko'rinishini tanlang:", reply_markup=get_visibility_keyboard())


@router.message(ImportStates.new_quiz_visibility)
async def prompt_visibility_fallback_import(message: Message) -> None:
    await message.answer("Iltimos, tugmalardan birini tanlang:", reply_markup=get_visibility_keyboard())


@router.callback_query(VisibilityCallback.filter(), ImportStates.new_quiz_visibility)
async def process_import_visibility(callback: CallbackQuery, callback_data: VisibilityCallback, state: FSMContext) -> None:
    await callback.answer()
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    if user is None:
        await callback.message.edit_text("❌ Foydalanuvchi ma'lumotlari topilmadi.")
        await state.clear()
        return
    data = await state.get_data()
    quiz = await create_quiz(
        created_by=user,
        title=data["new_title"],
        visibility=callback_data.value,
        time_per_question_sec=data["new_time"],
        source=Quiz.Source.IMPORT,
    )
    if quiz is None:
        await callback.message.edit_text("❌ Test yaratishda xatolik. Qayta urinib ko'ring.")
        await state.clear()
        return
    await state.update_data(quiz_id=quiz.id, quiz_title=quiz.title)
    blocked = await _check_limit_and_set_file_state(callback.message, state, callback.from_user.id, edit=True)
    if blocked:
        return


# --- mavjud test tanlash ---

@router.callback_query(QuizSelectCallback.filter(), ImportStates.choosing_existing_quiz)
async def process_existing_quiz_select(callback: CallbackQuery, callback_data: QuizSelectCallback, state: FSMContext) -> None:
    await callback.answer()
    quiz = await get_quiz_by_id(callback_data.quiz_id)
    if quiz is None:
        await callback.message.edit_text("❌ Test topilmadi.")
        await state.clear()
        return
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    if user is None or quiz.created_by_id != user.id:
        await callback.message.edit_text("⛔ Bu test sizga tegishli emas.")
        await state.clear()
        return
    await state.update_data(quiz_id=quiz.id, quiz_title=quiz.title)
    blocked = await _check_limit_and_set_file_state(callback.message, state, callback.from_user.id, edit=True)
    if blocked:
        return


# --- fayl qabul qilish ---

@router.message(ImportStates.awaiting_file, F.document)
async def process_import_file(message: Message, state: FSMContext, bot: Bot) -> None:
    doc = message.document
    filename = doc.file_name or "file"
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if suffix not in ("xlsx", "csv"):
        await message.answer("⚠️ Faqat .xlsx yoki .csv fayl yuboring.")
        return

    if doc.file_size and doc.file_size > _MAX_FILE_BYTES:
        await message.answer("⚠️ Fayl 20 MB dan katta bo'lmasligi kerak.")
        return

    data = await state.get_data()
    quiz_id = data.get("quiz_id")
    tg_user_id = message.from_user.id

    user = await get_or_create_user(tg_user_id, message.from_user.username)
    if user is None:
        await message.answer("❌ Foydalanuvchi topilmadi.")
        return

    max_files, max_rows = await get_import_limits()
    today_count = await count_imports_today(user.id)
    if today_count >= max_files:
        await message.answer(f"❌ Kunlik import limiti tugadi ({max_files} ta/kun). Ertaga qayta urinib ko'ring.")
        return

    status_msg = await message.answer("⏳ Fayl yuklanmoqda...")
    file_io = BytesIO()
    await bot.download(doc, destination=file_io)
    file_io.seek(0)

    try:
        df = read_dataframe(file_io, filename)
    except ValueError as e:
        await status_msg.edit_text(f"❌ {e}")
        return

    missing = check_required_columns(df)
    if missing:
        await status_msg.edit_text(
            f"❌ Faylda kerakli ustunlar yetishmayapti: <code>{', '.join(missing)}</code>\n\n"
            f"Zarur ustunlar: savol, variant_a, variant_b, variant_c, variant_d, togri_javob, izoh, qiyinlik",
            parse_mode="HTML",
        )
        return

    total_rows = len(df)
    if total_rows > max_rows:
        await status_msg.edit_text(
            f"❌ Fayl {total_rows} ta qator o'z ichiga oladi, limit: {max_rows} ta."
        )
        return

    if total_rows > _PROGRESS_CHUNK:
        await status_msg.edit_text(f"⏳ Ishlanmoqda... 0/{total_rows} (0%)")
        valid_rows, error_rows = validate_rows(df)
        asyncio.create_task(
            _process_with_progress(
                status_msg=status_msg,
                quiz_id=quiz_id,
                valid_rows=valid_rows,
                error_rows=error_rows,
                total_rows=total_rows,
                user_id=user.id,
                filename=filename,
            )
        )
    else:
        valid_rows, error_rows = validate_rows(df)
        await _finish_import(
            status_msg=status_msg,
            quiz_id=quiz_id,
            valid_rows=valid_rows,
            error_rows=error_rows,
            total_rows=total_rows,
            user_id=user.id,
            filename=filename,
        )


@router.message(ImportStates.awaiting_file, ~F.document)
async def awaiting_file_fallback(message: Message) -> None:
    await message.answer("📎 Iltimos, .xlsx yoki .csv fayl yuboring (yoki /cancel, /done).")


# --- yordamchi funksiyalar ---

async def _check_limit_and_set_file_state(message, state: FSMContext, tg_user_id: int, edit: bool = False) -> bool:
    user = await get_or_create_user(tg_user_id, None)
    if user is None:
        text = "❌ Foydalanuvchi topilmadi."
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        await state.clear()
        return True

    max_files, _ = await get_import_limits()
    today_count = await count_imports_today(user.id)
    if today_count >= max_files:
        text = f"❌ Kunlik import limiti tugadi ({max_files} ta/kun). Ertaga qayta urinib ko'ring."
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        await state.clear()
        return True

    data = await state.get_data()
    quiz_title = data.get("quiz_title", "")
    await state.set_state(ImportStates.awaiting_file)
    text = (
        f"✅ Tayyor. <b>{quiz_title}</b> testiga savol qo'shiladi.\n\n"
        f"📎 Endi <code>.xlsx</code> yoki <code>.csv</code> faylni yuboring.\n"
        f"Import tugagach /done deb yozing."
    )
    if edit:
        await message.edit_text(text, parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")
    return False


async def _safe_edit(msg, text: str) -> None:
    try:
        await msg.edit_text(text, parse_mode="HTML")
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after + 0.5)
        try:
            await msg.edit_text(text, parse_mode="HTML")
        except (TelegramBadRequest, TelegramRetryAfter):
            logger.warning("_safe_edit: ikkinchi urinishda ham xato")
    except TelegramBadRequest:
        pass


async def _process_with_progress(
    status_msg,
    quiz_id: int,
    valid_rows: list[dict],
    error_rows: list[dict],
    total_rows: int,
    user_id: int,
    filename: str,
) -> None:
    try:
        done = 0
        last_edit = 0.0
        chunk_size = _PROGRESS_CHUNK

        for i in range(0, len(valid_rows), chunk_size):
            chunk = valid_rows[i : i + chunk_size]
            await bulk_create_questions(quiz_id, chunk)
            done += len(chunk)
            now = time.monotonic()
            if now - last_edit >= _PROGRESS_MIN_INTERVAL:
                pct = round(100 * done / max(len(valid_rows), 1))
                await _safe_edit(status_msg, f"⏳ Ishlanmoqda... {done}/{len(valid_rows)} ({pct}%)")
                last_edit = now

        await _safe_edit(status_msg, f"⏳ Yakunlanmoqda... 100%")
        await create_import_log(
            user_id=user_id,
            filename=filename,
            total_rows=total_rows,
            success_count=len(valid_rows),
            error_count=len(error_rows),
            error_details=error_rows,
        )
        report = _build_report(len(valid_rows), error_rows, total_rows)
        await _safe_edit(status_msg, report)

    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("_process_with_progress kutilmagan xato: quiz_id=%s", quiz_id)
        await _safe_edit(status_msg, "❌ Import jarayonida xatolik yuz berdi.")


async def _finish_import(
    status_msg,
    quiz_id: int,
    valid_rows: list[dict],
    error_rows: list[dict],
    total_rows: int,
    user_id: int,
    filename: str,
) -> None:
    added = await bulk_create_questions(quiz_id, valid_rows)
    await create_import_log(
        user_id=user_id,
        filename=filename,
        total_rows=total_rows,
        success_count=added,
        error_count=len(error_rows),
        error_details=error_rows,
    )
    report = _build_report(added, error_rows, total_rows)
    await _safe_edit(status_msg, report)


def _build_report(success: int, error_rows: list[dict], total_rows: int) -> str:
    lines = [
        f"✅ Import yakunlandi!\n",
        f"📊 Jami qatorlar: <b>{total_rows}</b>",
        f"✔️ Muvaffaqiyatli: <b>{success}</b>",
        f"❌ Xatoli: <b>{len(error_rows)}</b>",
    ]
    if error_rows:
        lines.append("\n⚠️ Xatolar (birinchi 20 ta):")
        for e in error_rows[:20]:
            lines.append(f"  • {e['row']}-qator: {e['reason']}")
        if len(error_rows) > 20:
            lines.append(f"  ... va yana {len(error_rows) - 20} ta xato.")
    lines.append("\nTuzatib qayta yuborishingiz yoki /done deb yozishingiz mumkin.")
    return "\n".join(lines)
