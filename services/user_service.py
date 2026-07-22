import logging

from asgiref.sync import sync_to_async
from django.db import DatabaseError, IntegrityError

from apps.users.models import User, UserSettings

logger = logging.getLogger(__name__)


@sync_to_async
def get_or_create_user(telegram_id: int, username: str | None) -> User | None:
    try:
        user, created = User.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={"username": username},
        )
        if not created and username and user.username != username:
            user.username = username
            user.save(update_fields=["username"])
        if created:
            UserSettings.objects.get_or_create(user=user)
        return user
    except (IntegrityError, DatabaseError):
        logger.exception("get_or_create_user xato: telegram_id=%s", telegram_id)
        return None


def is_admin_role(user: User) -> bool:
    return user.role in (User.Role.ADMIN, User.Role.SUPER_ADMIN)


@sync_to_async
def get_user_settings(user_id: int) -> UserSettings | None:
    try:
        settings_obj, _ = UserSettings.objects.get_or_create(user_id=user_id)
        return settings_obj
    except DatabaseError:
        logger.exception("get_user_settings xato: user_id=%s", user_id)
        return None


@sync_to_async
def toggle_user_setting(user_id: int, field: str) -> UserSettings | None:
    allowed_fields = {"hide_share_button", "notifications_on"}
    if field not in allowed_fields:
        logger.warning("toggle_user_setting: noto'g'ri maydon=%s", field)
        return None
    try:
        settings_obj, _ = UserSettings.objects.get_or_create(user_id=user_id)
        current = getattr(settings_obj, field)
        setattr(settings_obj, field, not current)
        settings_obj.save(update_fields=[field])
        return settings_obj
    except DatabaseError:
        logger.exception("toggle_user_setting xato: user_id=%s, field=%s", user_id, field)
        return None
