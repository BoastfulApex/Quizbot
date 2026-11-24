import logging

from aiogram import Bot, Router
from aiogram.filters import IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated

from services.group_service import deactivate_group, update_member_count, upsert_group

logger = logging.getLogger(__name__)

router = Router(name="group_handler")


@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def bot_added_to_group(event: ChatMemberUpdated, bot: Bot) -> None:
    chat = event.chat
    if chat.type not in ("group", "supergroup"):
        return

    username = chat.username or None
    await upsert_group(chat_id=chat.id, title=chat.title or str(chat.id), username=username)

    try:
        count = await bot.get_chat_member_count(chat.id)
        await update_member_count(chat.id, count)
    except Exception:
        logger.exception("bot_added_to_group: a'zolar soni olishda xato, chat_id=%s", chat.id)

    logger.info("Bot guruhga qo'shildi: %s (%s)", chat.title, chat.id)


@router.my_chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def bot_removed_from_group(event: ChatMemberUpdated) -> None:
    chat = event.chat
    if chat.type not in ("group", "supergroup"):
        return

    await deactivate_group(chat.id)
    logger.info("Bot guruhdan chiqarildi: %s (%s)", chat.title, chat.id)
