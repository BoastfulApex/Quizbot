# QuizBot

Telegram test-viktorina boti — har qanday foydalanuvchi test yarata oladigan (UGC) platforma,
Excel/CSV import, AI orqali savol generatsiya, guruhga share/unshare, avtomatik rejalashtirish
va Django asosidagi web admin panel bilan.

To'liq talablar: [docs/TZ.md](docs/TZ.md).

## Stack

- Bot: Python 3.12, aiogram 3.x
- Web admin: Django 5.x + PostgreSQL 16 (yagona baza, Django ORM yagona manba)
- AI: Anthropic Claude API
- Fayl import: pandas, openpyxl
- Rejalashtirish: APScheduler

## Lokal ishga tushirish

1. `.env.example` ni `.env` ga nusxalab, qiymatlarni to'ldiring (`BOT_TOKEN`,
   `ANTHROPIC_API_KEY`, Postgres ma'lumotlari, `DJANGO_SECRET_KEY`).
2. Bog'liqliklarni o'rnating: `pip install -r requirements.txt`.
3. Postgres'ni ko'taring: `docker-compose up -d db`.
4. Migratsiyalarni bajaring: `docker-compose run --rm web python manage.py migrate`.
5. Web admin va botni ishga tushiring: `docker-compose up web bot`.

Admin panel: `http://localhost:8000/admin/` (superuser yaratish uchun:
`docker-compose run --rm web python manage.py createsuperuser`).

## Testlar

```
pytest
```
