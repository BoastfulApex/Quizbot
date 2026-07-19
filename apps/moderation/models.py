from django.db import models

from apps.quizzes.models import Quiz
from apps.users.models import User


class ImportLimitSettings(models.Model):
    SINGLETON_ID = 1

    max_files_per_day = models.PositiveIntegerField(default=3)
    max_rows_per_file = models.PositiveIntegerField(default=5000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "import_limit_settings"
        verbose_name = "Import limiti sozlamalari"
        verbose_name_plural = "Import limiti sozlamalari"

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_ID
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls) -> "ImportLimitSettings":
        obj, _ = cls.objects.get_or_create(pk=cls.SINGLETON_ID)
        return obj

    def __str__(self):
        return f"Import limiti: {self.max_files_per_day} fayl/kun, {self.max_rows_per_file} qator/fayl"


class ImportLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="import_logs")
    filename = models.CharField(max_length=255)
    total_rows = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    error_details_json = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "import_logs"

    def __str__(self):
        return f"ImportLog({self.user_id}, {self.filename})"


class AiGenerationLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_generation_logs")
    topic = models.CharField(max_length=255)
    questions_count = models.PositiveIntegerField(default=0)
    model_used = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_generation_logs"

    def __str__(self):
        return f"AiGenerationLog({self.user_id}, {self.topic})"


class Report(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        REVIEWED = "reviewed", "Reviewed"
        DISMISSED = "dismissed", "Dismissed"

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="reports")
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reports")
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reports"

    def __str__(self):
        return f"Report({self.quiz_id}, {self.status})"
