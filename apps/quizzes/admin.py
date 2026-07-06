from django.contrib import admin

from apps.quizzes.models import (
    Answer,
    GroupSharedQuiz,
    Question,
    Quiz,
    QuizSession,
    Schedule,
)


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "category",
        "created_by",
        "visibility",
        "source",
        "moderation_status",
        "is_active",
        "created_at",
    )
    list_filter = ("visibility", "source", "moderation_status", "is_active")
    search_fields = ("title", "description")
    inlines = [QuestionInline]


@admin.register(QuizSession)
class QuizSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "user", "chat_id", "score", "started_at", "finished_at")
    list_filter = ("started_at",)
    search_fields = ("quiz__title", "user__username")


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "question", "selected_option", "is_correct", "time_taken_sec")
    list_filter = ("is_correct",)


@admin.register(GroupSharedQuiz)
class GroupSharedQuizAdmin(admin.ModelAdmin):
    list_display = ("id", "chat_id", "quiz", "shared_by", "is_active", "shared_at", "unshared_at")
    list_filter = ("is_active",)
    search_fields = ("quiz__title", "shared_by__username")


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "quiz",
        "cron_expression",
        "run_once_at",
        "target_chat_id",
        "is_active",
        "created_by",
    )
    list_filter = ("is_active",)
    search_fields = ("quiz__title",)
