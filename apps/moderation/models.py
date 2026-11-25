from django.db import models

from apps.quizzes.models import Quiz
from apps.users.models import User


class AiProviderSettings(models.Model):
    class Provider(models.TextChoices):
        GEMINI = "gemini", "Google Gemini"
        CLAUDE = "claude", "Anthropic Claude"
        OPENAI = "openai", "OpenAI GPT"

    SINGLETON_ID = 1

    active_provider = models.CharField(
        max_length=20, choices=Provider.choices, default=Provider.GEMINI,
        verbose_name="Faol AI provayder",
    )
    gemini_api_key = models.CharField(max_length=500, blank=True, verbose_name="Gemini API kaliti")
    gemini_model = models.CharField(max_length=100, default="gemini-flash-lite-latest", verbose_name="Gemini modeli")
    claude_api_key = models.CharField(max_length=500, blank=True, verbose_name="Claude API kaliti")
    claude_model = models.CharField(max_length=100, default="claude-opus-4-8", verbose_name="Claude modeli")
    openai_api_key = models.CharField(max_length=500, blank=True, verbose_name="OpenAI API kaliti")
    openai_model = models.CharField(max_length=100, default="gpt-4o", verbose_name="OpenAI modeli")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_provider_settings"
        verbose_name = "AI provayder sozlamalari"
        verbose_name_plural = "AI provayder sozlamalari"

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_ID
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls) -> "AiProviderSettings":
        obj, _ = cls.objects.get_or_create(pk=cls.SINGLETON_ID)
        return obj

    def __str__(self):
        return f"AI sozlamalari ({self.get_active_provider_display()})"


class BotGroup(models.Model):
    chat_id = models.BigIntegerField(unique=True, db_index=True, verbose_name="Chat ID")
    title = models.CharField(max_length=255, verbose_name="Guruh nomi")
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name="Username")
    member_count = models.PositiveIntegerField(default=0, verbose_name="A'zolar soni")
    is_active = models.BooleanField(default=True, verbose_name="Bot guruhda")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Qo'shilgan vaqt")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bot_groups"
        verbose_name = "Guruh"
        verbose_name_plural = "Guruhlar"
        ordering = ["-added_at"]

    def __str__(self):
        return self.title or str(self.chat_id)


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
    class Status(models.TextChoices):
        SUCCESS = "success", "Muvaffaqiyatli"
        FAILED = "failed", "Xatolik"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_generation_logs",
                             verbose_name="Foydalanuvchi")
    topic = models.CharField(max_length=255, verbose_name="Mavzu")
    source_filename = models.CharField(max_length=255, blank=True, verbose_name="Fayl")
    requested_count = models.PositiveIntegerField(default=0, verbose_name="So'ralgan savollar")
    questions_count = models.PositiveIntegerField(default=0, verbose_name="Yaratilgan savollar")
    model_used = models.CharField(max_length=100, blank=True, verbose_name="Model")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUCCESS,
                              db_index=True, verbose_name="Holat")
    error_message = models.TextField(blank=True, verbose_name="Xatolik sababi")
    error_details = models.TextField(blank=True, verbose_name="Texnik tafsilot")
    duration_ms = models.PositiveIntegerField(default=0, verbose_name="Davomiylik (ms)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Vaqt")

    class Meta:
        db_table = "ai_generation_logs"
        verbose_name = "AI generatsiya"
        verbose_name_plural = "AI generatsiyalar"
        ordering = ["-created_at"]

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
