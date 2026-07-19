import asyncio
from io import BytesIO

import pandas as pd
import pytest

from apps.moderation.models import ImportLimitSettings, ImportLog
from apps.quizzes.models import Question, Quiz
from apps.users.models import User
from services.import_service import (
    bulk_create_questions,
    check_required_columns,
    count_imports_today,
    create_import_log,
    get_import_limits,
    read_dataframe,
    validate_rows,
)


@pytest.fixture
def user(db):
    return User.objects.create(telegram_id=10, username="importer")


@pytest.fixture
def other_user(db):
    return User.objects.create(telegram_id=11, username="other_importer")


@pytest.fixture
def quiz(user):
    return Quiz.objects.create(title="Import testi", created_by=user)


# --- get_import_limits ---

@pytest.mark.django_db(transaction=True)
def test_get_import_limits_defaults_when_no_settings():
    max_files, max_rows = asyncio.run(get_import_limits())

    assert max_files == 3
    assert max_rows == 5000


@pytest.mark.django_db(transaction=True)
def test_get_import_limits_returns_configured_values():
    ImportLimitSettings.objects.update_or_create(
        pk=ImportLimitSettings.SINGLETON_ID,
        defaults={"max_files_per_day": 10, "max_rows_per_file": 2000},
    )

    max_files, max_rows = asyncio.run(get_import_limits())

    assert max_files == 10
    assert max_rows == 2000


# --- count_imports_today ---

@pytest.mark.django_db(transaction=True)
def test_count_imports_today_counts_todays_logs(user):
    ImportLog.objects.create(user=user, filename="a.xlsx", total_rows=10, success_count=10, error_count=0)
    ImportLog.objects.create(user=user, filename="b.xlsx", total_rows=5, success_count=5, error_count=0)

    result = asyncio.run(count_imports_today(user.id))

    assert result == 2


@pytest.mark.django_db(transaction=True)
def test_count_imports_today_excludes_other_user(user, other_user):
    ImportLog.objects.create(user=other_user, filename="x.xlsx", total_rows=1, success_count=1, error_count=0)

    result = asyncio.run(count_imports_today(user.id))

    assert result == 0


# --- bulk_create_questions ---

@pytest.mark.django_db(transaction=True)
def test_bulk_create_questions_inserts_all_rows(quiz):
    rows = [
        {
            "question_text": f"Savol {i}",
            "option_a": "A", "option_b": "B", "option_c": "C", "option_d": "D",
            "correct_option": "A", "explanation": "", "difficulty": "",
        }
        for i in range(3)
    ]

    count = asyncio.run(bulk_create_questions(quiz.id, rows))

    assert count == 3
    assert Question.objects.filter(quiz=quiz).count() == 3


@pytest.mark.django_db(transaction=True)
def test_bulk_create_questions_returns_zero_for_missing_quiz():
    rows = [{"question_text": "S", "option_a": "A", "option_b": "B", "option_c": "C", "option_d": "D",
              "correct_option": "A", "explanation": "", "difficulty": ""}]

    count = asyncio.run(bulk_create_questions(999999, rows))

    assert count == 0


@pytest.mark.django_db(transaction=True)
def test_bulk_create_questions_empty_rows_returns_zero(quiz):
    count = asyncio.run(bulk_create_questions(quiz.id, []))

    assert count == 0


# --- create_import_log ---

@pytest.mark.django_db(transaction=True)
def test_create_import_log_success(user):
    log = asyncio.run(
        create_import_log(
            user_id=user.id,
            filename="test.xlsx",
            total_rows=100,
            success_count=95,
            error_count=5,
            error_details=[{"row": 3, "reason": "bo'sh savol"}],
        )
    )

    assert log is not None
    assert log.user_id == user.id
    assert log.success_count == 95
    assert log.error_count == 5
    assert len(log.error_details_json) == 1


@pytest.mark.django_db(transaction=True)
def test_create_import_log_returns_none_for_missing_user():
    result = asyncio.run(
        create_import_log(
            user_id=999999,
            filename="x.xlsx",
            total_rows=1,
            success_count=1,
            error_count=0,
            error_details=[],
        )
    )

    assert result is None


# --- read_dataframe ---

_CSV_HEADER = "savol,variant_a,variant_b,variant_c,variant_d,togri_javob,izoh,qiyinlik"


def _make_csv(rows: str, header: str = _CSV_HEADER) -> BytesIO:
    content = f"{header}\n{rows}".encode("utf-8")
    return BytesIO(content)


def test_read_dataframe_csv_success():
    buf = _make_csv("Savol 1,A,B,C,D,A,Izoh,oson")
    df = read_dataframe(buf, "test.csv")

    assert len(df) == 1
    assert "savol" in df.columns


def test_read_dataframe_unknown_extension_raises():
    buf = BytesIO(b"data")
    with pytest.raises(ValueError, match="Faqat .xlsx yoki .csv"):
        read_dataframe(buf, "file.txt")


# --- check_required_columns ---

def test_check_required_columns_no_missing():
    buf = _make_csv("S,A,B,C,D,A,I,oson")
    df = read_dataframe(buf, "f.csv")

    assert check_required_columns(df) == []


def test_check_required_columns_missing_column():
    buf = _make_csv(
        "S,A,B,C,D,A,I,oson",
        header="savol,variant_a,variant_b,variant_c,variant_d,togri_javob,izoh",
    )
    df = read_dataframe(buf, "f.csv")

    missing = check_required_columns(df)
    assert "qiyinlik" in missing


# --- validate_rows ---

def _df(*rows):
    cols = ["savol", "variant_a", "variant_b", "variant_c", "variant_d", "togri_javob", "izoh", "qiyinlik"]
    return pd.DataFrame([dict(zip(cols, r)) for r in rows], columns=cols)


def test_validate_rows_valid_row():
    df = _df(("Savol?", "A", "B", "C", "D", "A", "Izoh", "oson"))
    valid, errors = validate_rows(df)

    assert len(valid) == 1
    assert errors == []
    assert valid[0]["correct_option"] == "A"


def test_validate_rows_empty_question():
    df = _df(("", "A", "B", "C", "D", "A", "", "oson"))
    valid, errors = validate_rows(df)

    assert valid == []
    assert len(errors) == 1
    assert "bo'sh" in errors[0]["reason"]


def test_validate_rows_invalid_correct_option():
    df = _df(("Savol?", "A", "B", "C", "D", "E", "", "oson"))
    valid, errors = validate_rows(df)

    assert valid == []
    assert any("togri_javob" in e["reason"] for e in errors)


def test_validate_rows_question_too_long():
    long_q = "x" * 300
    df = _df((long_q, "A", "B", "C", "D", "B", "", "oson"))
    valid, errors = validate_rows(df)

    assert valid == []
    assert any("belgidan uzun" in e["reason"] for e in errors)


def test_validate_rows_duplicate_question():
    df = _df(
        ("Bir xil savol", "A", "B", "C", "D", "A", "", "oson"),
        ("Bir xil savol", "A", "B", "C", "D", "B", "", "oson"),
    )
    valid, errors = validate_rows(df)

    assert len(valid) == 1
    assert len(errors) == 1
    assert "dublikat" in errors[0]["reason"]


def test_validate_rows_row_number_is_correct():
    df = _df(
        ("Savol 1", "A", "B", "C", "D", "A", "", "oson"),
        ("", "A", "B", "C", "D", "A", "", "oson"),
    )
    _, errors = validate_rows(df)

    assert errors[0]["row"] == 3
