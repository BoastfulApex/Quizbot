import logging
import re
from io import BytesIO

from asgiref.sync import sync_to_async
from django.db import DatabaseError
from docx import Document
from docx.enum.text import WD_BREAK
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


def build_docx(quiz: Quiz, questions: list[Question]) -> bytes:
    doc = Document()
    doc.add_heading(quiz.title, level=1)
    doc.add_paragraph(f"Savollar soni: {len(questions)}")

    for number, question in enumerate(questions, start=1):
        doc.add_paragraph(f"{number}. {question.question_text}").runs[0].bold = True
        for letter in _OPTION_LETTERS:
            doc.add_paragraph(f"{letter}) {getattr(question, f'option_{letter.lower()}')}")

    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    doc.add_heading("Javoblar kaliti", level=2)
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    for cell, label in zip(table.rows[0].cells, ("№", "Javob", "Izoh")):
        cell.text = label
    for number, question in enumerate(questions, start=1):
        row = table.add_row().cells
        row[0].text = str(number)
        row[1].text = question.correct_option
        row[2].text = question.explanation

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
