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
    list_display = ("created_at", "user", "source_display", "status_badge", "count_display",
                    "model_used", "duration_display", "short_error")
    list_display_links = ("created_at", "source_display")
    list_filter = ("status", "model_used", "created_at")
    search_fields = ("topic", "source_filename", "error_message", "user__username", "user__telegram_id")
    date_hierarchy = "created_at"
    list_select_related = ("user",)
    list_per_page = 50
    fieldsets = (
        (None, {"fields": ("status_badge", "created_at", "user", "topic", "source_filename")}),
        ("Natija", {"fields": ("requested_count", "questions_count", "model_used", "duration_display")}),
        ("Xatolik", {"fields": ("error_message", "error_details_pre")}),
    )
    readonly_fields = ("status_badge", "created_at", "user", "topic", "source_filename", "requested_count",
                       "questions_count", "model_used", "duration_display", "error_message", "error_details_pre")

    @admin.display(description="Manba")
    def source_display(self, obj):
        if obj.source_filename:
            return f"📄 {obj.source_filename}"
        return f"✏️ {obj.topic}"

    @admin.display(description="Holat", ordering="status")
    def status_badge(self, obj):
        if obj.status == AiGenerationLog.Status.FAILED:
            return format_html('<span class="qb-badge qb-badge--bad">✗ Xatolik</span>')
        return format_html('<span class="qb-badge qb-badge--ok">✓ Muvaffaqiyatli</span>')

    @admin.display(description="Savollar")
    def count_display(self, obj):
        if obj.requested_count:
            return f"{obj.questions_count} / {obj.requested_count}"
        return obj.questions_count

    @admin.display(description="Davomiylik", ordering="duration_ms")
    def duration_display(self, obj):
        return f"{obj.duration_ms / 1000:.1f} s" if obj.duration_ms else "—"

    @admin.display(description="Xatolik sababi")
    def short_error(self, obj):
        if not obj.error_message:
            return "—"
        text = obj.error_message if len(obj.error_message) <= 90 else obj.error_message[:87] + "..."
        return format_html('<span class="qb-error-text">{}</span>', text)

    @admin.display(description="Texnik tafsilot")
    def error_details_pre(self, obj):
        if not obj.error_details:
            return "—"
        return format_html('<pre class="qb-trace">{}</pre>', obj.error_details)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Report, site=admin_site)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "reported_by", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("quiz__title", "reported_by__username")
