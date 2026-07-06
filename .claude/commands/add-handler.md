---
description: Yangi aiogram handler qo'shish (router, keyboard, state bilan birga)
---

Foydalanuvchi berilgan buyruq/callback uchun yangi handler yaratish kerak: $ARGUMENTS

Quyidagi tartibda bajaring:

1. `bot/handlers/users/` (yoki tegishli bo'lsa `admins/`) ichida mos fayl toping
   yoki yarating.
2. Agar handler FSM state talab qilsa — `bot/states/` ga mos `State` klass qo'shing.
3. Agar inline/default keyboard kerak bo'lsa — `bot/keyboards/inline/` yoki
   `bot/keyboards/default/` ga alohida funksiya sifatida qo'shing (handler ichida
   keyboard yaratilmasin).
4. Handler ichida biznes-mantiqni yozmang — `services/` dan mos funksiyani chaqiring.
   Agar mos servis funksiyasi yo'q bo'lsa, avval uni `services/` da yarating.
5. Egalik tekshiruvi kerak bo'lgan amallar uchun `.claude/rules/ownership.md` ga amal
   qiling — middleware yoki servis darajasida tekshiring, handler ichida emas.
6. Yangi handlerni tegishli `router`ga ulang va `handlers/__init__.py` da ro'yxatga
   olinganini tekshiring.
7. `tests/` ga mos test qo'shing (kamida: muvaffaqiyatli holat + ruxsat rad etilgan holat).
