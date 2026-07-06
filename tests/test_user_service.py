import asyncio

import pytest

from apps.users.models import UserSettings
from services.user_service import get_or_create_user


@pytest.mark.django_db
def test_get_or_create_user_is_idempotent_and_creates_settings():
    user1 = asyncio.run(get_or_create_user(telegram_id=42, username="alice"))
    user2 = asyncio.run(get_or_create_user(telegram_id=42, username="alice"))

    assert user1 is not None
    assert user1.id == user2.id
    assert UserSettings.objects.filter(user=user1).exists()


@pytest.mark.django_db
def test_get_or_create_user_returns_none_on_missing_telegram_id():
    result = asyncio.run(get_or_create_user(telegram_id=None, username="bob"))

    assert result is None
