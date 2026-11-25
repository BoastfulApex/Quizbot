import logging
from html import escape
from pathlib import Path

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from bot.handlers.users.quiz import launch_quiz_from_deep_link
from bot.keyboards.default.menu import get_main_menu
from bot.utils.texts import HELP_TEXT, WELCOME_TEXT
from services.user_service import get_or_create_user, is_admin_role

logger = logging.getLogger(__name__)

router = Router(name="start")

_WELCOME_IMAGE = Path(__file__).resolve().parents[2] / "assets" / "welcome.png"
# Rasm Telegram'ga bir marta yuklanadi, keyin file_id orqali qayta ishlatiladi.
_welcome_file_id: str | None = None


async def _send_welcome(message: Message) -> bool:
    """Xush kelibsiz xabarini (rasm + matn) yuboradi. Foydalanuvchi topilmasa False."""
    global _welcome_file_id

    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
    )
    if user is None:
        await message.answer("Kechirasiz, xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.")
        return False

    name = escape(message.from_user.first_name or message.from_user.username or "foydalanuvchi")
    text = WELCOME_TEXT.format(name=name)
    menu = get_main_menu(is_admin=is_admin_role(user))

    if _WELCOME_IMAGE.exists():
        photo = _welcome_file_id or FSInputFile(_WELCOME_IMAGE)
        try:
            sent = await message.answer_photo(photo, caption=text, reply_markup=menu)
            _welcome_file_id = sent.photo[-1].file_id
            return True
        except TelegramBadRequest:
            logger.exception("welcome rasmini yuborib bo'lmadi, matn yuboriladi")
            _welcome_file_id = None

    await message.answer(text, reply_markup=menu)
    return True


@router.message(CommandStart(deep_link=True))
async def cmd_start_deep_link(message: Message, command: CommandObject, state: FSMContext) -> None:
    if not await _send_welcome(message):
        return

    payload = command.args or ""
    if payload.startswith("quiz_") and payload[5:].isdigit():
        await launch_quiz_from_deep_link(message, int(payload[5:]), state)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await _send_welcome(message)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
