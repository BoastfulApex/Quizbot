from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message

from bot.keyboards.default.menu import MAIN_MENU_BUTTONS


class MenuResetMiddleware(BaseMiddleware):
    """Oqim o'rtasida asosiy menyu tugmasi bosilsa — oqimni tugatib, tugmani odatdagidek ishlatadi.

    Aks holda masalan "📂 Mening testlarim" matni test sarlavhasi sifatida saqlanib qolardi.
    Outer middleware bo'lgani uchun filtrlardan oldin ishlaydi va ``raw_state`` ni ham tozalaydi.
    """

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        state = data.get("state")
        if (
            state is not None
            and event.chat.type == "private"
            and event.text in MAIN_MENU_BUTTONS
            and data.get("raw_state") is not None
        ):
            await state.clear()
            data["raw_state"] = None
        return await handler(event, data)
