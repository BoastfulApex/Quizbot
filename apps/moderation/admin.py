from django.contrib import admin

from apps.moderation.models import AiGenerationLog, ImportLimitSettings, ImportLog, Report


@admin.register(ImportLimitSettings)
class ImportLimitSettingsAdmin(admin.ModelAdmin):
    list_display = ("max_files_per_day", "max_rows_per_file", "updated_at")

    def has_add_permission(self, request):
        return not ImportLimitSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "filename", "total_rows", "success_count", "error_count", "created_at")
    list_filter = ("created_at",)
    search_fields = ("filename", "user__username")


@admin.register(AiGenerationLog)
class AiGenerationLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "topic", "questions_count", "model_used", "created_at")
    list_filter = ("model_used",)
    search_fields = ("topic", "user__username")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "reported_by", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("quiz__title", "reported_by__username")
