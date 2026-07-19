import asyncio

import pytest

from apps.quizzes.models import GroupSharedQuiz, Question, Quiz, QuizSession
from apps.users.models import User
from services.quiz_service import (
    add_question,
    create_quiz,
    find_quiz_by_name_or_id,
    finish_session,
    get_group_shared_quizzes,
    get_questions_for_quiz,
    get_quizzes_created_by,
    get_session_ranking,
    get_session_stats,
    get_user_and_public_quizzes,
    start_quiz_session,
    submit_answer,
)


@pytest.fixture
def user(db):
    return User.objects.create(telegram_id=1, username="owner")


@pytest.fixture
def other_user(db):
    return User.objects.create(telegram_id=2, username="other")


@pytest.mark.django_db(transaction=True)
def test_create_quiz_success(user):
    quiz = asyncio.run(create_quiz(created_by=user, title="Geografiya", visibility=Quiz.Visibility.PUBLIC))

    assert quiz is not None
    assert quiz.created_by_id == user.id
    assert quiz.visibility == Quiz.Visibility.PUBLIC


@pytest.mark.django_db(transaction=True)
def test_create_quiz_returns_none_for_title_too_long(user):
    result = asyncio.run(create_quiz(created_by=user, title="x" * 300))

    assert result is None


@pytest.mark.django_db(transaction=True)
def test_create_quiz_with_custom_time_per_question(user):
    quiz = asyncio.run(create_quiz(created_by=user, title="Vaqtli test", time_per_question_sec=15))

    assert quiz.time_per_question_sec == 15


@pytest.mark.django_db(transaction=True)
def test_create_quiz_default_time_per_question(user):
    quiz = asyncio.run(create_quiz(created_by=user, title="Standart"))

    assert quiz.time_per_question_sec == 30


@pytest.mark.django_db(transaction=True)
def test_get_questions_for_quiz_returns_ordered_list(user):
    quiz = Quiz.objects.create(title="Savollar", created_by=user)
    q1 = Question.objects.create(
        quiz=quiz, question_text="1", option_a="a", option_b="b", option_c="c", option_d="d", correct_option="A"
    )
    q2 = Question.objects.create(
        quiz=quiz, question_text="2", option_a="a", option_b="b", option_c="c", option_d="d", correct_option="B"
    )

    result = asyncio.run(get_questions_for_quiz(quiz.id))

    assert [q.id for q in result] == [q1.id, q2.id]


@pytest.mark.django_db(transaction=True)
def test_get_questions_for_quiz_empty_for_missing_quiz():
    result = asyncio.run(get_questions_for_quiz(999999))

    assert result == []


@pytest.mark.django_db(transaction=True)
def test_add_question_success(user):
    quiz = Quiz.objects.create(title="Tarix", created_by=user)

    question = asyncio.run(
        add_question(
            quiz_id=quiz.id,
            question_text="Savol?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_option="A",
        )
    )

    assert question is not None
    assert question.quiz_id == quiz.id


@pytest.mark.django_db(transaction=True)
def test_add_question_returns_none_for_missing_quiz():
    result = asyncio.run(
        add_question(
            quiz_id=999999,
            question_text="Savol?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_option="A",
        )
    )

    assert result is None


@pytest.mark.django_db(transaction=True)
def test_get_user_and_public_quizzes_includes_own_and_public(user, other_user):
    own = Quiz.objects.create(title="Mening", created_by=user, visibility=Quiz.Visibility.PRIVATE)
    Quiz.objects.create(title="Boshqa private", created_by=other_user, visibility=Quiz.Visibility.PRIVATE)
    public = Quiz.objects.create(
        title="Ommaviy",
        created_by=other_user,
        visibility=Quiz.Visibility.PUBLIC,
        moderation_status=Quiz.ModerationStatus.APPROVED,
    )

    result = asyncio.run(get_user_and_public_quizzes(user.id))
    ids = {q.id for q in result}

    assert own.id in ids
    assert public.id in ids


@pytest.mark.django_db(transaction=True)
def test_get_user_and_public_quizzes_empty_for_new_user(user):
    result = asyncio.run(get_user_and_public_quizzes(user.id))

    assert result == []


@pytest.mark.django_db(transaction=True)
def test_find_quiz_by_id_exact_match(user):
    quiz = Quiz.objects.create(title="ABC", created_by=user)

    result = asyncio.run(find_quiz_by_name_or_id(str(quiz.id), user.id))

    assert len(result) == 1
    assert result[0].id == quiz.id


@pytest.mark.django_db(transaction=True)
def test_find_quiz_by_name_no_match(user):
    result = asyncio.run(find_quiz_by_name_or_id("mavjud-emas", user.id))

    assert result == []


@pytest.mark.django_db(transaction=True)
def test_get_group_shared_quizzes_returns_active_shares(user):
    quiz = Quiz.objects.create(title="Guruh testi", created_by=user)
    GroupSharedQuiz.objects.create(chat_id=555, quiz=quiz, shared_by=user)

    result = asyncio.run(get_group_shared_quizzes(555))

    assert len(result) == 1
    assert result[0].id == quiz.id


@pytest.mark.django_db(transaction=True)
def test_get_group_shared_quizzes_empty_when_none_shared():
    result = asyncio.run(get_group_shared_quizzes(999))

    assert result == []


@pytest.mark.django_db(transaction=True)
def test_start_quiz_session_success(user):
    quiz = Quiz.objects.create(title="Bilim", created_by=user)
    Question.objects.create(
        quiz=quiz, question_text="S1", option_a="a", option_b="b", option_c="c", option_d="d", correct_option="A"
    )

    session = asyncio.run(start_quiz_session(quiz.id, user.id, chat_id=100))

    assert session is not None
    assert session.quiz_id == quiz.id


@pytest.mark.django_db(transaction=True)
def test_start_quiz_session_returns_none_without_questions(user):
    quiz = Quiz.objects.create(title="Bosh test", created_by=user)

    result = asyncio.run(start_quiz_session(quiz.id, user.id, chat_id=100))

    assert result is None


@pytest.mark.django_db(transaction=True)
def test_submit_answer_correct_updates_score(user):
    quiz = Quiz.objects.create(title="Test", created_by=user)
    question = Question.objects.create(
        quiz=quiz, question_text="S1", option_a="a", option_b="b", option_c="c", option_d="d", correct_option="B"
    )
    session = QuizSession.objects.create(quiz=quiz, user=user, chat_id=1)

    result = asyncio.run(submit_answer(session.id, question.id, "B", time_taken_sec=5))

    assert result is not None
    answer, returned_question = result
    assert answer.is_correct is True
    assert returned_question.id == question.id
    session.refresh_from_db()
    assert session.score == 1


@pytest.mark.django_db(transaction=True)
def test_submit_answer_duplicate_returns_none(user):
    quiz = Quiz.objects.create(title="Test", created_by=user)
    question = Question.objects.create(
        quiz=quiz, question_text="S1", option_a="a", option_b="b", option_c="c", option_d="d", correct_option="A"
    )
    session = QuizSession.objects.create(quiz=quiz, user=user, chat_id=1)

    asyncio.run(submit_answer(session.id, question.id, "A", time_taken_sec=3))
    result = asyncio.run(submit_answer(session.id, question.id, "B", time_taken_sec=3))

    assert result is None


@pytest.mark.django_db(transaction=True)
def test_get_session_stats_success(user):
    quiz = Quiz.objects.create(title="Statistika", created_by=user)
    q1 = Question.objects.create(
        quiz=quiz, question_text="S1", option_a="a", option_b="b", option_c="c", option_d="d", correct_option="A"
    )
    Question.objects.create(
        quiz=quiz, question_text="S2", option_a="a", option_b="b", option_c="c", option_d="d", correct_option="B"
    )
    session = QuizSession.objects.create(quiz=quiz, user=user, chat_id=1)
    asyncio.run(submit_answer(session.id, q1.id, "C", time_taken_sec=4))
    asyncio.run(finish_session(session.id))

    stats = asyncio.run(get_session_stats(session.id))

    assert stats["total_questions"] == 2
    assert stats["correct"] == 0
    assert stats["wrong"] == 1
    assert stats["skipped"] == 1
    assert stats["duration_sec"] is not None


@pytest.mark.django_db(transaction=True)
def test_get_session_stats_returns_none_for_missing_session():
    result = asyncio.run(get_session_stats(999999))

    assert result is None


@pytest.mark.django_db(transaction=True)
def test_get_session_ranking_orders_by_score(user, other_user):
    quiz = Quiz.objects.create(title="Reyting", created_by=user)
    session_high = QuizSession.objects.create(quiz=quiz, user=user, chat_id=1, score=5)
    session_low = QuizSession.objects.create(quiz=quiz, user=other_user, chat_id=1, score=2)
    asyncio.run(finish_session(session_high.id))
    asyncio.run(finish_session(session_low.id))

    ranking_high = asyncio.run(get_session_ranking(session_high.id))
    ranking_low = asyncio.run(get_session_ranking(session_low.id))

    assert ranking_high["rank"] == 1
    assert ranking_high["total"] == 2
    assert ranking_high["percent_better"] == 100
    assert ranking_low["rank"] == 2
    assert ranking_low["percent_better"] == 0


@pytest.mark.django_db(transaction=True)
def test_get_session_ranking_single_session_no_percent(user):
    quiz = Quiz.objects.create(title="Yagona", created_by=user)
    session = QuizSession.objects.create(quiz=quiz, user=user, chat_id=1, score=3)
    asyncio.run(finish_session(session.id))

    ranking = asyncio.run(get_session_ranking(session.id))

    assert ranking["rank"] == 1
    assert ranking["total"] == 1
    assert ranking["percent_better"] is None


@pytest.mark.django_db(transaction=True)
def test_get_session_ranking_returns_none_for_missing_session():
    result = asyncio.run(get_session_ranking(999999))

    assert result is None


@pytest.mark.django_db(transaction=True)
def test_get_quizzes_created_by_returns_own_quizzes(user):
    q1 = Quiz.objects.create(title="Mening 1", created_by=user)
    q2 = Quiz.objects.create(title="Mening 2", created_by=user)

    result = asyncio.run(get_quizzes_created_by(user.id))
    ids = {q.id for q in result}

    assert q1.id in ids
    assert q2.id in ids


@pytest.mark.django_db(transaction=True)
def test_get_quizzes_created_by_excludes_others_public(user, other_user):
    Quiz.objects.create(
        title="Boshqa public",
        created_by=other_user,
        visibility=Quiz.Visibility.PUBLIC,
        moderation_status=Quiz.ModerationStatus.APPROVED,
    )

    result = asyncio.run(get_quizzes_created_by(user.id))

    assert result == []
