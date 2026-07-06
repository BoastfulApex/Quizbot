from django.contrib import admin

from apps.users.models import User, UserSettings


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "telegram_id", "username", "role", "is_blocked", "created_at")
    list_filter = ("role", "is_blocked")
    search_fields = ("username", "telegram_id")


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "hide_share_button", "notifications_on", "language")
    list_filter = ("hide_share_button", "notifications_on", "language")
    search_fields = ("user__username", "user__telegram_id")
