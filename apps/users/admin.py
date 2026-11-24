from django.contrib import admin
from django.utils.html import format_html

from apps.moderation.site import admin_site
from apps.users.models import User, UserSettings


@admin.register(User, site=admin_site)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "telegram_id", "username", "role", "blocked_badge", "created_at")
    list_filter = ("role", "is_blocked")
    search_fields = ("username", "telegram_id")
    actions = ["block_users", "unblock_users"]

    def blocked_badge(self, obj):
        if obj.is_blocked:
            return format_html('<span style="color:#db4437;font-weight:600;">🚫 Bloklangan</span>')
        return format_html('<span style="color:#0f9d58;">✓ Faol</span>')
    blocked_badge.short_description = "Holat"

    @admin.action(description="Tanlangan foydalanuvchilarni bloklash")
    def block_users(self, request, queryset):
        queryset.update(is_blocked=True)

    @admin.action(description="Tanlangan foydalanuvchilarni ochish")
    def unblock_users(self, request, queryset):
        queryset.update(is_blocked=False)


@admin.register(UserSettings, site=admin_site)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "hide_share_button", "notifications_on", "language")
    list_filter = ("hide_share_button", "notifications_on", "language")
    search_fields = ("user__username", "user__telegram_id")
