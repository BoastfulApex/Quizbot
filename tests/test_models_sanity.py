import pytest
from django.db import IntegrityError

from apps.quizzes.models import GroupSharedQuiz, Quiz
from apps.users.models import User


@pytest.mark.django_db
def test_quiz_created_by_relation():
    user = User.objects.create(telegram_id=1, username="owner")
    quiz = Quiz.objects.create(title="Test quiz", created_by=user)

    assert quiz.created_by_id == user.id
    assert user.quizzes.count() == 1


@pytest.mark.django_db
def test_group_shared_quiz_unique_chat_and_quiz():
    user = User.objects.create(telegram_id=2, username="sharer")
    quiz = Quiz.objects.create(title="Shared quiz", created_by=user)
    GroupSharedQuiz.objects.create(chat_id=100, quiz=quiz, shared_by=user)

    with pytest.raises(IntegrityError):
        GroupSharedQuiz.objects.create(chat_id=100, quiz=quiz, shared_by=user)
