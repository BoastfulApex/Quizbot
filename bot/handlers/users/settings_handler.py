import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.keyboards.default.menu import BTN_SETTINGS
from bot.keyboards.inline.settings_inline import (
    SettingsToggleCallback,
    build_settings_text,
    get_settings_keyboard,
)
from services.user_service import get_or_create_user, get_user_settings, toggle_user_setting

logger = logging.getLogger(__name__)

router = Router(name="settings")


@router.message(F.text == BTN_SETTINGS)
async def show_settings(message: Message) -> None:
    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    if user is None:
        await message.answer("❌ Xatolik yuz berdi.")
        return

    s = await get_user_settings(user.id)
    if s is None:
        await message.answer("❌ Sozlamalar yuklanmadi.")
        return

    await message.answer(
        build_settings_text(s),
        reply_markup=get_settings_keyboard(s),
        parse_mode="HTML",
    )


@router.callback_query(SettingsToggleCallback.filter())
async def toggle_setting(callback: CallbackQuery, callback_data: SettingsToggleCallback) -> None:
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    if user is None:
        await callback.answer("Xatolik yuz berdi.", show_alert=True)
        return

    s = await toggle_user_setting(user.id, callback_data.field)
    if s is None:
        await callback.answer("Sozlamani o'zgartirib bo'lmadi.", show_alert=True)
        return

    await callback.message.edit_text(
        build_settings_text(s),
        reply_markup=get_settings_keyboard(s),
        parse_mode="HTML",
    )
    await callback.answer()
