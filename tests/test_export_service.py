import asyncio
from io import BytesIO

import pytest
from docx import Document

from apps.quizzes.models import Question, Quiz
from apps.users.models import User
from services.export_service import build_docx, build_xlsx, export_filename, get_exportable_quiz
from services.import_service import check_required_columns, read_dataframe, validate_rows


@pytest.fixture
def owner(db):
    return User.objects.create(telegram_id=301, username="owner")


@pytest.fixture
def quiz(owner):
    quiz = Quiz.objects.create(created_by=owner, title="O'zbekiston tarixi")
    Question.objects.create(
        quiz=quiz, question_text="Amir Temur qachon tug'ilgan?",
        option_a="1336", option_b="1370", option_c="1405", option_d="1220",
        correct_option="A", explanation="1336-yil, Kesh yaqinida.",
    )
    Question.objects.create(
        quiz=quiz, question_text="Mustaqillik yili?",
        option_a="1990", option_b="1991", option_c="1992", option_d="1989",
        correct_option="B", explanation="",
    )
    return quiz


@pytest.mark.django_db(transaction=True)
def test_get_exportable_quiz_returns_owner_quiz(owner, quiz):
    result = asyncio.run(get_exportable_quiz(quiz.id, owner))

    assert result is not None
    found, questions = result
    assert found.id == quiz.id
    assert [q.correct_option for q in questions] == ["A", "B"]


@pytest.mark.django_db(transaction=True)
def test_get_exportable_quiz_rejects_other_user(quiz):
    stranger = User.objects.create(telegram_id=302, username="stranger")
    assert asyncio.run(get_exportable_quiz(quiz.id, stranger)) is None


@pytest.mark.django_db(transaction=True)
def test_get_exportable_quiz_allows_admin(quiz):
    admin = User.objects.create(telegram_id=303, username="admin", role=User.Role.ADMIN)
    assert asyncio.run(get_exportable_quiz(quiz.id, admin)) is not None


@pytest.mark.django_db(transaction=True)
def test_get_exportable_quiz_returns_none_for_inactive(owner, quiz):
    Quiz.objects.filter(id=quiz.id).update(is_active=False)
    assert asyncio.run(get_exportable_quiz(quiz.id, owner)) is None


@pytest.mark.django_db
def test_build_docx_contains_questions_and_answer_key(quiz):
    questions = list(quiz.questions.order_by("id"))
    doc = Document(BytesIO(build_docx(quiz, questions)))

    text = "\n".join(p.text for p in doc.paragraphs)
    assert "1. Amir Temur qachon tug'ilgan?" in text
    assert "B) 1370" in text
    assert "Javoblar kaliti" in text
    key_rows = [[c.text for c in row.cells] for row in doc.tables[0].rows]
    assert key_rows[1] == ["1", "A", "1336-yil, Kesh yaqinida."]
    assert key_rows[2][:2] == ["2", "B"]


@pytest.mark.django_db
def test_build_xlsx_round_trips_through_import(quiz):
    questions = list(quiz.questions.order_by("id"))
    df = read_dataframe(BytesIO(build_xlsx(questions)), "export.xlsx")

    assert check_required_columns(df) == []
    valid, errors = validate_rows(df)
    assert errors == []
    assert [row["question_text"] for row in valid] == [q.question_text for q in questions]
    assert valid[1]["correct_option"] == "B"
    assert valid[1]["explanation"] == ""


@pytest.mark.django_db
def test_export_filename_falls_back_when_title_has_no_word_chars(owner):
    quiz = Quiz.objects.create(created_by=owner, title="???")
    assert export_filename(quiz, "docx") == f"test_{quiz.id}.docx"
