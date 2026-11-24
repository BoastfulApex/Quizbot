# Bot handler qoidalari

- Har bir handler fayli bitta mantiqiy blokka tegishli: `quiz`, `import`, `generate`, `settings`, va h.k.
  Bir faylga bog'liq bo'lmagan handler qo'shilmaydi.
- Handler ichida DB ga to'g'ridan-to'g'ri kirish **taqiqlanadi** — faqat `services/*.py` orqali,
  `sync_to_async` bilan o'ralgan holda.
- FSM state'lari `bot/states/` papkasida alohida modul sifatida saqlanadi — handler faylining
  ichida `StatesGroup` aniqlanmaydi.
- Har bir handler `Router()` dan foydalanadi va `bot/run.py` da `dp.include_router()` orqali
  ro'yxatga olinadi — `dp` ga to'g'ridan-to'g'ri `@dp.message(...)` yozilmaydi.
- Egalik tekshiruvi handler ichida emas, `services/` yoki `bot/middlewares/ownership_check.py`
  darajasida amalga oshirilishi shart.
- Private chat'ga mo'ljallangan handler boshida `F.chat.type == "private"` filtri bo'lishi kerak.
- Foydalanuvchiga xabar yuborishda HTML parse mode ishlatiladi: `parse_mode="HTML"`.
- Callback query handlerlar oxirida `await callback.answer()` chaqirilishi shart.
