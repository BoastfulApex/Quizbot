from django.contrib import admin
from django.utils import timezone


class QuizBotAdminSite(admin.AdminSite):
    site_header = "QuizBot Admin"
    site_title = "QuizBot"
    index_title = "Boshqaruv paneli"

    def index(self, request, extra_context=None):
        from apps.moderation.models import AiGenerationLog, AiProviderSettings, BotGroup
        from apps.quizzes.models import Quiz
        from apps.users.models import User

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timezone.timedelta(days=7)

        ai_settings = AiProviderSettings.load()
        model_map = {
            "gemini": ai_settings.gemini_model,
            "claude": ai_settings.claude_model,
            "openai": ai_settings.openai_model,
        }

        stats = {
            "total_users": User.objects.count(),
            "users_today": User.objects.filter(created_at__gte=today_start).count(),
            "users_week": User.objects.filter(created_at__gte=week_start).count(),
            "total_groups": BotGroup.objects.count(),
            "active_groups": BotGroup.objects.filter(is_active=True).count(),
            "total_quizzes": Quiz.objects.count(),
            "manual_quizzes": Quiz.objects.filter(source=Quiz.Source.MANUAL).count(),
            "import_quizzes": Quiz.objects.filter(source=Quiz.Source.IMPORT).count(),
            "ai_quizzes": Quiz.objects.filter(source=Quiz.Source.AI).count(),
            "total_ai_logs": AiGenerationLog.objects.count(),
            "ai_today": AiGenerationLog.objects.filter(created_at__gte=today_start).count(),
            "active_provider": ai_settings.get_active_provider_display(),
            "active_model": model_map.get(ai_settings.active_provider, "—"),
        }
        extra_context = extra_context or {}
        extra_context["stats"] = stats
        return super().index(request, extra_context)


admin_site = QuizBotAdminSite(name="quizbot_admin")
