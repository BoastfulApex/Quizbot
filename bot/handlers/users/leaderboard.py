from aiogram import F, Router
from aiogram.types import Message

from bot.keyboards.default.menu import BTN_LEADERBOARD
from bot.utils.texts import GUIDE_LEADERBOARD

router = Router(name="leaderboard")


@router.message(F.text == BTN_LEADERBOARD)
async def guide_leaderboard(message: Message) -> None:
    await message.answer(GUIDE_LEADERBOARD)
