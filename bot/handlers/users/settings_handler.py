from aiogram import F, Router
from aiogram.types import Message

from bot.keyboards.default.menu import BTN_SETTINGS
from bot.utils.texts import GUIDE_SETTINGS

router = Router(name="settings")


@router.message(F.text == BTN_SETTINGS)
async def guide_settings(message: Message) -> None:
    await message.answer(GUIDE_SETTINGS)
