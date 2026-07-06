from aiogram import F, Router
from aiogram.types import Message

from bot.keyboards.default.menu import BTN_ADMIN_PANEL
from bot.utils.texts import GUIDE_ADMIN_PANEL
from services.user_service import get_or_create_user, is_admin_role

router = Router(name="admin")


@router.message(F.text == BTN_ADMIN_PANEL)
async def guide_admin_panel(message: Message) -> None:
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
    )
    if user is None or not is_admin_role(user):
        return

    await message.answer(GUIDE_ADMIN_PANEL)
