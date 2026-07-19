import logging
from io import BytesIO

import pandas as pd
from asgiref.sync import sync_to_async
from django.db import DatabaseError, IntegrityError
from django.utils import timezone

from apps.moderation.models import ImportLimitSettings, ImportLog
from apps.quizzes.models import Question, Quiz
from bot.utils.limits import MAX_EXPLANATION_LEN, MAX_OPTION_LEN, MAX_QUESTION_LEN

logger = logging.getLogger(__name__)

_FALLBACK_MAX_FILES_PER_DAY = 3
_FALLBACK_MAX_ROWS_PER_FILE = 5000

REQUIRED_COLUMNS = ["savol", "variant_a", "variant_b", "variant_c", "variant_d", "togri_javob", "izoh", "qiyinlik"]
VALID_OPTIONS = {"A", "B", "C", "D"}


@sync_to_async
def get_import_limits() -> tuple[int, int]:
    try:
        limits = ImportLimitSettings.load()
        return limits.max_files_per_day, limits.max_rows_per_file
    except DatabaseError:
        logger.exception("get_import_limits xato")
        return _FALLBACK_MAX_FILES_PER_DAY, _FALLBACK_MAX_ROWS_PER_FILE


@sync_to_async
def count_imports_today(user_id: int) -> int:
    try:
        return ImportLog.objects.filter(user_id=user_id, created_at__date=timezone.localdate()).count()
    except DatabaseError:
        logger.exception("count_imports_today xato: user_id=%s", user_id)
        return 0


@sync_to_async
def bulk_create_questions(quiz_id: int, rows: list[dict]) -> int:
    if not rows:
        return 0
    try:
        quiz = Quiz.objects.get(id=quiz_id)
    except Quiz.DoesNotExist:
        logger.warning("bulk_create_questions: quiz topilmadi, quiz_id=%s", quiz_id)
        return 0
    except DatabaseError:
        logger.exception("bulk_create_questions: quiz olishda xato, quiz_id=%s", quiz_id)
        return 0

    questions = [
        Question(
            quiz=quiz,
            question_text=row["question_text"],
            option_a=row["option_a"],
            option_b=row["option_b"],
            option_c=row["option_c"],
            option_d=row["option_d"],
            correct_option=row["correct_option"],
            explanation=row.get("explanation", ""),
            difficulty=row.get("difficulty", ""),
        )
        for row in rows
    ]
    try:
        created = Question.objects.bulk_create(questions)
        return len(created)
    except (IntegrityError, DatabaseError):
        logger.exception("bulk_create_questions xato: quiz_id=%s, count=%s", quiz_id, len(questions))
        return 0


@sync_to_async
def create_import_log(
    user_id: int,
    filename: str,
    total_rows: int,
    success_count: int,
    error_count: int,
    error_details: list[dict],
) -> ImportLog | None:
    try:
        return ImportLog.objects.create(
            user_id=user_id,
            filename=filename,
            total_rows=total_rows,
            success_count=success_count,
            error_count=error_count,
            error_details_json=error_details,
        )
    except (IntegrityError, DatabaseError):
        logger.exception("create_import_log xato: user_id=%s, filename=%s", user_id, filename)
        return None


def read_dataframe(file_bytes: BytesIO, filename: str) -> pd.DataFrame:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    try:
        if suffix == "csv":
            try:
                df = pd.read_csv(file_bytes, dtype=str, keep_default_na=False, encoding="utf-8-sig")
            except UnicodeDecodeError:
                file_bytes.seek(0)
                df = pd.read_csv(file_bytes, dtype=str, keep_default_na=False, encoding="cp1251")
        elif suffix == "xlsx":
            df = pd.read_excel(file_bytes, engine="openpyxl", dtype=str, keep_default_na=False)
        else:
            raise ValueError("Faqat .xlsx yoki .csv fayl qabul qilinadi.")
    except (pd.errors.ParserError, ValueError, OSError) as e:
        raise ValueError(f"Faylni o'qib bo'lmadi: {e}") from e

    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def check_required_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in REQUIRED_COLUMNS if c not in df.columns]


def validate_rows(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    valid_rows: list[dict] = []
    error_rows: list[dict] = []
    seen_questions: set[str] = set()

    for idx, raw in df.iterrows():
        row_number = int(idx) + 2  # sarlavha = 1-qator
        row = {col: str(raw[col]).strip() for col in REQUIRED_COLUMNS}
        errors: list[str] = []

        if not row["savol"]:
            errors.append("savol matni bo'sh")
        elif len(row["savol"]) > MAX_QUESTION_LEN:
            errors.append(f"savol {MAX_QUESTION_LEN} belgidan uzun")

        for col in ("variant_a", "variant_b", "variant_c", "variant_d"):
            if not row[col]:
                errors.append(f"{col} bo'sh")
            elif len(row[col]) > MAX_OPTION_LEN:
                errors.append(f"{col} {MAX_OPTION_LEN} belgidan uzun")

        correct = row["togri_javob"].upper()
        if correct not in VALID_OPTIONS:
            errors.append(f"togri_javob noto'g'ri: '{row['togri_javob']}' (faqat A/B/C/D)")

        if len(row["izoh"]) > MAX_EXPLANATION_LEN:
            errors.append(f"izoh {MAX_EXPLANATION_LEN} belgidan uzun")

        key = row["savol"].lower()
        if row["savol"] and key in seen_questions:
            errors.append("fayl ichida takrorlangan savol (dublikat)")

        if errors:
            error_rows.append({"row": row_number, "reason": "; ".join(errors)})
            continue

        seen_questions.add(key)
        valid_rows.append({
            "question_text": row["savol"],
            "option_a": row["variant_a"],
            "option_b": row["variant_b"],
            "option_c": row["variant_c"],
            "option_d": row["variant_d"],
            "correct_option": correct,
            "explanation": row["izoh"],
            "difficulty": row["qiyinlik"],
        })

    return valid_rows, error_rows
