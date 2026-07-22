from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.users.models import UserSettings


class SettingsToggleCallback(CallbackData, prefix="stg"):
    field: str


def get_settings_keyboard(s: UserSettings) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    notif_label = "🔔 Bildirishnomalar: ✅ Yoqilgan" if s.notifications_on else "🔔 Bildirishnomalar: ❌ O'chirilgan"
    share_label = "🔗 Share tugmasi: 👁 Ko'rinadi" if not s.hide_share_button else "🔗 Share tugmasi: 🙈 Yashirilgan"

    builder.button(text=notif_label, callback_data=SettingsToggleCallback(field="notifications_on"))
    builder.button(text=share_label, callback_data=SettingsToggleCallback(field="hide_share_button"))
    builder.adjust(1)
    return builder.as_markup()


def build_settings_text(s: UserSettings) -> str:
    notif = "✅ Yoqilgan" if s.notifications_on else "❌ O'chirilgan"
    share = "👁 Ko'rinadi" if not s.hide_share_button else "🙈 Yashirilgan"
    return (
        "⚙️ <b>Sozlamalar</b>\n\n"
        f"🔔 Bildirishnomalar: {notif}\n"
        f"🔗 Share tugmasi: {share}\n\n"
        "O'zgartirish uchun tugmani bosing:"
    )
