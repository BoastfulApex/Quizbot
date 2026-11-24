import logging

from asgiref.sync import sync_to_async
from django.db import DatabaseError

from apps.moderation.models import BotGroup

logger = logging.getLogger(__name__)


@sync_to_async
def upsert_group(chat_id: int, title: str, username: str | None = None) -> BotGroup | None:
    try:
        group, _ = BotGroup.objects.update_or_create(
            chat_id=chat_id,
            defaults={"title": title, "username": username or "", "is_active": True},
        )
        return group
    except DatabaseError:
        logger.exception("upsert_group xato: chat_id=%s", chat_id)
        return None


@sync_to_async
def deactivate_group(chat_id: int) -> None:
    try:
        BotGroup.objects.filter(chat_id=chat_id).update(is_active=False)
    except DatabaseError:
        logger.exception("deactivate_group xato: chat_id=%s", chat_id)


@sync_to_async
def update_member_count(chat_id: int, count: int) -> None:
    try:
        BotGroup.objects.filter(chat_id=chat_id).update(member_count=count)
    except DatabaseError:
        logger.exception("update_member_count xato: chat_id=%s", chat_id)
