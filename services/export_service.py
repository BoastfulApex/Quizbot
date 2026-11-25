import logging
import re
from io import BytesIO

from asgiref.sync import sync_to_async
from django.db import DatabaseError
from docx import Document
from openpyxl import Workbook
from openpyxl.styles import Font

from apps.quizzes.models import Question, Quiz
from apps.users.models import User
from services.import_service import REQUIRED_COLUMNS
from services.user_service import is_admin_role

logger = logging.getLogger(__name__)

_OPTION_LETTERS = ("A", "B", "C", "D")
_MAX_FILENAME_LEN = 50


@sync_to_async
def get_exportable_quiz(quiz_id: int, user: User) -> tuple[Quiz, list[Question]] | None:
    try:
        quiz = Quiz.objects.get(id=quiz_id, is_active=True)
        if quiz.created_by_id != user.id and not is_admin_role(user):
            logger.warning("get_exportable_quiz: egasi emas, quiz_id=%s, user_id=%s", quiz_id, user.id)
            return None
        return quiz, list(quiz.questions.order_by("id"))
    except Quiz.DoesNotExist:
        return None
    except DatabaseError:
        logger.exception("get_exportable_quiz xato: quiz_id=%s, user_id=%s", quiz_id, user.id)
        return None


def export_filename(quiz: Quiz, extension: str) -> str:
    base = re.sub(r"[^\w\-]+", "_", quiz.title, flags=re.UNICODE).strip("_")[:_MAX_FILENAME_LEN]
    return f"{base or f'test_{quiz.id}'}.{extension}"


def _options_correct_first(question: Question) -> list[str]:
    correct = question.correct_option
    others = [letter for letter in _OPTION_LETTERS if letter != correct]
    return [getattr(question, f"option_{letter.lower()}") for letter in [correct, *others]]


def build_docx(quiz: Quiz, questions: list[Question]) -> bytes:
    doc = Document()
    for question in questions:
        rows = [question.question_text, *_options_correct_first(question)]
        table = doc.add_table(rows=len(rows), cols=1)
        table.style = "Table Grid"
        for row, text in zip(table.rows, rows):
            row.cells[0].text = text
        doc.add_paragraph()

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_xlsx(questions: list[Question]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Savollar"
    ws.append(REQUIRED_COLUMNS)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for question in questions:
        ws.append([
            question.question_text,
            question.option_a,
            question.option_b,
            question.option_c,
            question.option_d,
            question.correct_option,
            question.explanation,
            question.difficulty,
        ])

    ws.column_dimensions["A"].width = 60
    for column in "BCDE":
        ws.column_dimensions[column].width = 30
    ws.column_dimensions["G"].width = 40

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
