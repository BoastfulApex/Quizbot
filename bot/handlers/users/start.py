import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.handlers.users.quiz import launch_quiz_from_deep_link
from bot.keyboards.default.menu import get_main_menu
from bot.utils.texts import HELP_TEXT, WELCOME_TEXT
from services.user_service import get_or_create_user, is_admin_role

logger = logging.getLogger(__name__)

router = Router(name="start")


@router.message(CommandStart(deep_link=True))
async def cmd_start_deep_link(message: Message, command: CommandObject, state: FSMContext) -> None:
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
    )
    if user is None:
        await message.answer("Kechirasiz, xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.")
        return

    name = message.from_user.first_name or message.from_user.username or "foydalanuvchi"
    await message.answer(
        WELCOME_TEXT.format(name=name),
        reply_markup=get_main_menu(is_admin=is_admin_role(user)),
    )

    payload = command.args or ""
    if payload.startswith("quiz_") and payload[5:].isdigit():
        await launch_quiz_from_deep_link(message, int(payload[5:]), state)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
    )
    if user is None:
        await message.answer("Kechirasiz, xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.")
        return

    name = message.from_user.first_name or message.from_user.username or "foydalanuvchi"
    await message.answer(
        WELCOME_TEXT.format(name=name),
        reply_markup=get_main_menu(is_admin=is_admin_role(user)),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
