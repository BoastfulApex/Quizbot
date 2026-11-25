import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.keyboards.inline.nav_inline import NavCallback
from bot.utils.flow_steps import STEPS, ask
from services.quiz_service import count_questions, delete_quiz
from services.user_service import get_or_create_user

logger = logging.getLogger(__name__)
router = Router(name=__name__)


async def _edit_or_answer(callback: CallbackQuery, text: str) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=None)
    except TelegramBadRequest:
        logger.debug("nav: xabarni tahrirlab bo'lmadi, yangisi yuboriladi")
        await callback.message.answer(text)


async def _cancel_flow(callback: CallbackQuery, state: FSMContext) -> None:
    if await state.get_state() is None:
        await callback.answer("Bu tugma eskirgan.")
        return

    data = await state.get_data()
    await state.clear()

    text = "❌ Bekor qilindi."
    created_quiz_id = data.get("created_quiz_id")
    if created_quiz_id:
        total = await count_questions(created_quiz_id)
        if total == 0:
            user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
            if user is not None and await delete_quiz(created_quiz_id, user):
                text = "❌ Bekor qilindi. Savolsiz qolgan test o'chirildi."
        else:
            text = (
                f"❌ Bekor qilindi. Test {total} ta savol bilan saqlandi — "
                f"📂 Mening testlarim bo'limida ko'rishingiz mumkin."
            )

    await _edit_or_answer(callback, text)
    await callback.answer()


@router.callback_query(NavCallback.filter(F.action == "cancel"))
async def nav_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await _cancel_flow(callback, state)


@router.callback_query(NavCallback.filter(F.action == "back"))
async def nav_back(callback: CallbackQuery, state: FSMContext) -> None:
    current = await state.get_state()
    step = STEPS.get(current) if current else None
    if step is None or step.prev is None:
        await _cancel_flow(callback, state)
        return

    await ask(callback.message, state, step.prev, edit=True)
    await callback.answer()


@router.callback_query(NavCallback.filter(F.action == "close"))
async def nav_close(callback: CallbackQuery) -> None:
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        logger.debug("nav_close: xabarni o'chirib bo'lmadi, faqat tugmalar olinadi")
        await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
