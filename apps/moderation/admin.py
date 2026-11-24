from django.contrib import admin
from django.utils.html import format_html

from apps.moderation.models import (
    AiGenerationLog,
    AiProviderSettings,
    BotGroup,
    ImportLimitSettings,
    ImportLog,
    Report,
)
from apps.moderation.site import admin_site


@admin.register(AiProviderSettings, site=admin_site)
class AiProviderSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Faol provayder", {
            "fields": ("active_provider",),
        }),
        ("Google Gemini", {
            "fields": ("gemini_api_key", "gemini_model"),
            "classes": ("collapse",),
        }),
        ("Anthropic Claude", {
            "fields": ("claude_api_key", "claude_model"),
            "classes": ("collapse",),
        }),
        ("OpenAI GPT", {
            "fields": ("openai_api_key", "openai_model"),
            "classes": ("collapse",),
        }),
    )
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        return not AiProviderSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj, _ = AiProviderSettings.objects.get_or_create(pk=AiProviderSettings.SINGLETON_ID)
        return self.change_view(request, str(obj.pk), extra_context=extra_context)


@admin.register(BotGroup, site=admin_site)
class BotGroupAdmin(admin.ModelAdmin):
    list_display = ("title", "chat_id", "username_link", "member_count", "status_badge", "added_at")
    list_filter = ("is_active",)
    search_fields = ("title", "username", "chat_id")
    readonly_fields = ("chat_id", "added_at", "updated_at")

    def username_link(self, obj):
        if obj.username:
            return format_html('<a href="https://t.me/{}" target="_blank">@{}</a>', obj.username, obj.username)
        return "—"
    username_link.short_description = "Username"

    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#0f9d58;font-weight:600;">✓ Faol</span>')
        return format_html('<span style="color:#db4437;">✗ Chiqarilgan</span>')
    status_badge.short_description = "Holat"

    def has_add_permission(self, request):
        return False


@admin.register(ImportLimitSettings, site=admin_site)
class ImportLimitSettingsAdmin(admin.ModelAdmin):
    list_display = ("max_files_per_day", "max_rows_per_file", "updated_at")

    def has_add_permission(self, request):
        return not ImportLimitSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = ImportLimitSettings.load()
        return self.change_view(request, str(obj.pk), extra_context=extra_context)


@admin.register(ImportLog, site=admin_site)
class ImportLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "filename", "total_rows", "success_count", "error_count", "created_at")
    list_filter = ("created_at",)
    search_fields = ("filename", "user__username")


@admin.register(AiGenerationLog, site=admin_site)
class AiGenerationLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "topic", "questions_count", "model_used", "created_at")
    list_filter = ("model_used", "created_at")
    search_fields = ("topic", "user__username")


@admin.register(Report, site=admin_site)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "reported_by", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("quiz__title", "reported_by__username")
