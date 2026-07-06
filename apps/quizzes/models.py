from django.db import models

from apps.users.models import User


class Quiz(models.Model):
    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        PUBLIC = "public", "Public"

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        IMPORT = "import", "Import"
        AI = "ai", "AI"

    class ModerationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    difficulty = models.CharField(max_length=20, blank=True)
    time_per_question_sec = models.PositiveIntegerField(default=30)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quizzes")
    is_active = models.BooleanField(default=True)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PRIVATE)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.MANUAL)
    moderation_status = models.CharField(
        max_length=20, choices=ModerationStatus.choices, default=ModerationStatus.APPROVED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "quizzes"

    def __str__(self):
        return self.title


class Question(models.Model):
    class CorrectOption(models.TextChoices):
        A = "A", "A"
        B = "B", "B"
        C = "C", "C"
        D = "D", "D"

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    option_a = models.CharField(max_length=500)
    option_b = models.CharField(max_length=500)
    option_c = models.CharField(max_length=500)
    option_d = models.CharField(max_length=500)
    correct_option = models.CharField(max_length=1, choices=CorrectOption.choices)
    explanation = models.TextField(blank=True)
    difficulty = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "questions"

    def __str__(self):
        return self.question_text[:50]


class QuizSession(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="sessions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quiz_sessions")
    chat_id = models.BigIntegerField()
    score = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "quiz_sessions"

    def __str__(self):
        return f"QuizSession({self.quiz_id}, {self.user_id})"


class Answer(models.Model):
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    selected_option = models.CharField(
        max_length=1, choices=Question.CorrectOption.choices, blank=True, null=True
    )
    is_correct = models.BooleanField(default=False)
    time_taken_sec = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "answers"

    def __str__(self):
        return f"Answer({self.session_id}, {self.question_id})"


class GroupSharedQuiz(models.Model):
    chat_id = models.BigIntegerField()
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="group_shares")
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shared_quizzes")
    shared_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    unshared_at = models.DateTimeField(null=True, blank=True)
    unshared_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="unshared_quizzes"
    )

    class Meta:
        db_table = "group_shared_quizzes"
        constraints = [
            models.UniqueConstraint(fields=["chat_id", "quiz"], name="uniq_chat_quiz"),
        ]

    def __str__(self):
        return f"GroupSharedQuiz({self.chat_id}, {self.quiz_id})"


class Schedule(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="schedules")
    cron_expression = models.CharField(max_length=100, blank=True, null=True)
    run_once_at = models.DateTimeField(null=True, blank=True)
    target_chat_id = models.BigIntegerField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="schedules")

    class Meta:
        db_table = "schedules"

    def __str__(self):
        return f"Schedule({self.quiz_id}, {self.target_chat_id})"
