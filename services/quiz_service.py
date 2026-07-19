import logging

from asgiref.sync import sync_to_async
from django.db import DatabaseError, IntegrityError
from django.db.models import F, Q
from django.utils import timezone

from apps.quizzes.models import Answer, Question, Quiz, QuizSession
from apps.users.models import User

logger = logging.getLogger(__name__)


@sync_to_async
def create_quiz(
    created_by: User,
    title: str,
    description: str = "",
    category: str = "",
    difficulty: str = "",
    visibility: str = Quiz.Visibility.PRIVATE,
    time_per_question_sec: int = 30,
    source: str = Quiz.Source.MANUAL,
) -> Quiz | None:
    try:
        return Quiz.objects.create(
            created_by=created_by,
            title=title,
            description=description,
            category=category,
            difficulty=difficulty,
            visibility=visibility,
            time_per_question_sec=time_per_question_sec,
            source=source,
        )
    except (IntegrityError, DatabaseError):
        logger.exception("create_quiz xato: created_by=%s, title=%s", created_by.id, title)
        return None


@sync_to_async
def add_question(
    quiz_id: int,
    question_text: str,
    option_a: str,
    option_b: str,
    option_c: str,
    option_d: str,
    correct_option: str,
    explanation: str = "",
    difficulty: str = "",
) -> Question | None:
    try:
        quiz = Quiz.objects.get(id=quiz_id)
        return Question.objects.create(
            quiz=quiz,
            question_text=question_text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_option=correct_option,
            explanation=explanation,
            difficulty=difficulty,
        )
    except Quiz.DoesNotExist:
        logger.warning("add_question: quiz topilmadi, quiz_id=%s", quiz_id)
        return None
    except (IntegrityError, DatabaseError):
        logger.exception("add_question xato: quiz_id=%s", quiz_id)
        return None


@sync_to_async
def count_questions(quiz_id: int) -> int:
    try:
        return Question.objects.filter(quiz_id=quiz_id).count()
    except DatabaseError:
        logger.exception("count_questions xato: quiz_id=%s", quiz_id)
        return 0


@sync_to_async
def get_quizzes_created_by(user_id: int) -> list[Quiz]:
    try:
        return list(Quiz.objects.filter(created_by_id=user_id, is_active=True).order_by("-created_at"))
    except DatabaseError:
        logger.exception("get_quizzes_created_by xato: user_id=%s", user_id)
        return []


@sync_to_async
def get_user_and_public_quizzes(user_id: int) -> list[Quiz]:
    try:
        return list(
            Quiz.objects.filter(is_active=True)
            .filter(
                Q(created_by_id=user_id)
                | Q(visibility=Quiz.Visibility.PUBLIC, moderation_status=Quiz.ModerationStatus.APPROVED)
            )
            .select_related("created_by")
            .order_by("-created_at")
        )
    except DatabaseError:
        logger.exception("get_user_and_public_quizzes xato: user_id=%s", user_id)
        return []


@sync_to_async
def find_quiz_by_name_or_id(query: str, user_id: int) -> list[Quiz]:
    try:
        if query.isdigit():
            quiz = Quiz.objects.filter(id=int(query), is_active=True).first()
            return [quiz] if quiz else []
        return list(
            Quiz.objects.filter(is_active=True, title__icontains=query)
            .filter(
                Q(created_by_id=user_id)
                | Q(visibility=Quiz.Visibility.PUBLIC, moderation_status=Quiz.ModerationStatus.APPROVED)
            )
            .order_by("-created_at")[:20]
        )
    except DatabaseError:
        logger.exception("find_quiz_by_name_or_id xato: query=%s", query)
        return []


@sync_to_async
def get_quiz_by_id(quiz_id: int) -> Quiz | None:
    try:
        return Quiz.objects.select_related("created_by").get(id=quiz_id, is_active=True)
    except Quiz.DoesNotExist:
        return None
    except DatabaseError:
        logger.exception("get_quiz_by_id xato: quiz_id=%s", quiz_id)
        return None


@sync_to_async
def get_group_shared_quizzes(chat_id: int) -> list[Quiz]:
    try:
        return list(
            Quiz.objects.filter(
                group_shares__chat_id=chat_id,
                group_shares__is_active=True,
                is_active=True,
            ).distinct()
        )
    except DatabaseError:
        logger.exception("get_group_shared_quizzes xato: chat_id=%s", chat_id)
        return []


@sync_to_async
def start_quiz_session(quiz_id: int, user_id: int, chat_id: int) -> QuizSession | None:
    try:
        quiz = Quiz.objects.get(id=quiz_id, is_active=True)
        if not quiz.questions.exists():
            logger.warning("start_quiz_session: savolsiz quiz, quiz_id=%s", quiz_id)
            return None
        return QuizSession.objects.create(quiz=quiz, user_id=user_id, chat_id=chat_id)
    except Quiz.DoesNotExist:
        return None
    except (IntegrityError, DatabaseError):
        logger.exception("start_quiz_session xato: quiz_id=%s, user_id=%s", quiz_id, user_id)
        return None


@sync_to_async
def get_questions_for_quiz(quiz_id: int) -> list[Question]:
    try:
        return list(Question.objects.filter(quiz_id=quiz_id).order_by("id"))
    except DatabaseError:
        logger.exception("get_questions_for_quiz xato: quiz_id=%s", quiz_id)
        return []


@sync_to_async
def submit_answer(
    session_id: int,
    question_id: int,
    selected_option: str | None,
    time_taken_sec: int | None,
) -> tuple[Answer, Question] | None:
    try:
        if Answer.objects.filter(session_id=session_id, question_id=question_id).exists():
            return None
        question = Question.objects.get(id=question_id)
        is_correct = bool(selected_option) and selected_option == question.correct_option
        answer = Answer.objects.create(
            session_id=session_id,
            question_id=question_id,
            selected_option=selected_option,
            is_correct=is_correct,
            time_taken_sec=time_taken_sec,
        )
        if is_correct:
            QuizSession.objects.filter(id=session_id).update(score=F("score") + 1)
        return answer, question
    except Question.DoesNotExist:
        logger.warning("submit_answer: savol topilmadi, question_id=%s", question_id)
        return None
    except (IntegrityError, DatabaseError):
        logger.exception("submit_answer xato: session_id=%s, question_id=%s", session_id, question_id)
        return None


@sync_to_async
def finish_session(session_id: int) -> QuizSession | None:
    try:
        session = QuizSession.objects.get(id=session_id)
        session.finished_at = timezone.now()
        session.save(update_fields=["finished_at"])
        return session
    except QuizSession.DoesNotExist:
        return None
    except DatabaseError:
        logger.exception("finish_session xato: session_id=%s", session_id)
        return None


@sync_to_async
def get_session_stats(session_id: int) -> dict | None:
    try:
        session = QuizSession.objects.select_related("quiz").get(id=session_id)
        answers = list(session.answers.all())
        correct = sum(1 for a in answers if a.is_correct)
        wrong = len(answers) - correct
        total_questions = session.quiz.questions.count()
        skipped = max(total_questions - len(answers), 0)
        duration_sec = None
        if session.finished_at is not None:
            duration_sec = int((session.finished_at - session.started_at).total_seconds())
        return {
            "quiz_title": session.quiz.title,
            "score": session.score,
            "total_questions": total_questions,
            "correct": correct,
            "wrong": wrong,
            "skipped": skipped,
            "duration_sec": duration_sec,
        }
    except QuizSession.DoesNotExist:
        return None
    except DatabaseError:
        logger.exception("get_session_stats xato: session_id=%s", session_id)
        return None


@sync_to_async
def get_session_ranking(session_id: int) -> dict | None:
    try:
        session = QuizSession.objects.get(id=session_id)
        sessions = QuizSession.objects.filter(quiz_id=session.quiz_id, finished_at__isnull=False)
        total = sessions.count()
        rank = sessions.filter(score__gt=session.score).count() + 1
        others = total - 1
        percent_better = (
            round(100 * sessions.filter(score__lt=session.score).count() / others) if others > 0 else None
        )
        return {"rank": rank, "total": total, "percent_better": percent_better}
    except QuizSession.DoesNotExist:
        return None
    except DatabaseError:
        logger.exception("get_session_ranking xato: session_id=%s", session_id)
        return None
