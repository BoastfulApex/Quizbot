import asyncio
import logging
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django

django.setup()

from bot.handlers.admins.admin import router as admin_router
from bot.handlers.users.ai_generate import router as ai_generate_router
from bot.handlers.users.import_handler import router as import_router
from bot.handlers.users.inline_query import router as inline_query_router
from bot.handlers.users.leaderboard import router as leaderboard_router
from bot.handlers.users.quiz import router as quiz_router
from bot.handlers.users.quiz_create import router as quiz_create_router
from bot.handlers.users.settings_handler import router as settings_router
from bot.handlers.users.start import router as start_router
from bot.loader import bot, dp


def register_routers() -> None:
    dp.include_router(start_router)
    dp.include_router(quiz_create_router)
    dp.include_router(import_router)
    dp.include_router(ai_generate_router)
    dp.include_router(quiz_router)
    dp.include_router(leaderboard_router)
    dp.include_router(settings_router)
    dp.include_router(admin_router)
    dp.include_router(inline_query_router)


async def main():
    logging.basicConfig(level=logging.INFO)
    register_routers()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
