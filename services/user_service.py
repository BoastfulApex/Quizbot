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
