from django.db import models


class User(models.Model):
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        ADMIN = "admin", "Admin"
        USER = "user", "User"

    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.username or str(self.telegram_id)


class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="settings")
    hide_share_button = models.BooleanField(default=False)
    notifications_on = models.BooleanField(default=True)
    language = models.CharField(max_length=10, default="uz")

    class Meta:
        db_table = "user_settings"

    def __str__(self):
        return f"UserSettings({self.user_id})"
