---
description: Web admin panelga (Django) yangi endpoint/sahifa qo'shish
---

Web admin panelga yangi funksiya qo'shish kerak: $ARGUMENTS

Tartib:

1. Tegishli app'ni aniqlang (`apps/quizzes`, `apps/users`, `apps/moderation`) —
   yangi domen bo'lsa, yangi app yarating (`python manage.py startapp <nom>` va
   `core/settings.py`dagi `INSTALLED_APPS`ga qo'shing).
2. Model o'zgarishi kerak bo'lsa: `models.py` ni tahrirlang →
   `python manage.py makemigrations <app_nomi>` → diffni tekshiring.
3. `views.py` ga funksiya/class-based view qo'shing; agar faqat ma'lumot ko'rish/CRUD
   bo'lsa, avval Django'ning tayyor `admin.py` (ModelAdmin) orqali yechish mumkinmi
   tekshiring — ko'p hollarda alohida view yozish shart emas.
4. `urls.py` ga yo'l qo'shing va asosiy `core/urls.py`da `include()` qilinganini
   tekshiring.
5. Bot (`services/`) shu model bilan ishlaydigan bo'lsa, servis funksiyasini ham
   yangilang — lekin Django view va aiogram handler bir xil servis funksiyasini
   chaqirishi kerak (mantiqni ikki joyda takrorlamang).
