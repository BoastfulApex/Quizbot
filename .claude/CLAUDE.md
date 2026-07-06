# QuizBot — loyiha konteksti

## Nima bu loyiha
Telegram test-viktorina boti. Har qanday foydalanuvchi test yarata oladi (UGC model),
Excel/CSV import, AI orqali mavzudan savol generatsiya, avtomatik rejalashtirish,
guruhga share/unshare, va Django asosidagi web admin panel.

## Stack
- **Bot:** Python 3.12, aiogram 3.x (async, polling)
- **Web admin:** Django 5.x + PostgreSQL (bitta umumiy baza, bot va admin panel bir xil
  Django ORM modellaridan foydalanadi — `apps/*/models.py` yagona manba)
- **AI:** Anthropic Claude API (savol generatsiyasi uchun)
- **Fayl import:** pandas, openpyxl
- **Rejalashtirish:** APScheduler

## Muhim arxitektura qarorlari (nega shunday qilingan)
1. **Django ORM yagona manba.** aiogram tomonida SQLAlchemy YO'Q — bot Django modellariga
   `sync_to_async` orqali kiradi (`services/*.py` ichida). Sabab: ikkita ORM bir xil jadval
   bilan ishlasa, migratsiya konflikti va sxema desinxronizatsiyasi paydo bo'ladi.
2. **`services/` — domen bo'yicha ajratilgan.** Har bir fayl bitta mas'uliyat: `quiz_service.py`,
   `import_service.py`, `ai_generator_service.py`, `share_service.py`, `scheduler_service.py`,
   `moderation_service.py`. Bitta "god file" (`database.py` ichida hammasi) qilinmaydi —
   buni oldingi loyiha (KpiProject) tahlilida aniq kamchilik sifatida ko'rgan edik.
3. **Egalik tekshiruvi majburiy.** Har bir test `created_by` ga ega. Har bir yozish/o'chirish/
   share amali oldidan `created_by == current_user_id` (yoki admin) tekshiriladi —
   `bot/middlewares/ownership_check.py` va `services/share_service.py` da markazlashgan.
4. **Share faqat test egasiga tegishli.** Boshqa hech kim (hatto testni ishlagan bo'lsa ham)
   guruhga share qila olmaydi. `group_shared_quizzes` jadvalida `UNIQUE(chat_id, quiz_id)`.
5. **Bot guruhga a'zo bo'lishi shart** — guruh ichida `/startTest` yoki umumiy reyting
   ishlashi uchun (Telegram Bot API cheklovi).

## Kodlash konventsiyalari
- Har bir DB/servis funksiyasi **aniq exception handling** bilan yoziladi — `except: pass`
  yoki `print(e)` ISHLATILMAYDI, doim `logging.exception(...)` orqali log qilinadi.
- Vaqtinchalik/eskirgan kod (`# commented out`, `.bak` fayllar) repo'ga commit qilinmaydi.
- Har bir yangi funksiya uchun `tests/` da mos test fayli kutiladi.

## To'liq talablar
Batafsil funksional/nofunksional talablar uchun: `docs/TZ.md` ga qarang (agar mavjud bo'lsa),
yoki suhbat tarixidagi TZ hujjatiga murojaat qiling.
