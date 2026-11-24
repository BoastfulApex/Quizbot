---
name: fix-and-build
description: Sintaks xatolarni tuzatish, testlarni ishga tushirish va natijani tekshirish
---

# /fix-and-build buyrug'i

## Tartib
1. O'zgartirilgan Python fayllarni `python -m py_compile` orqali tekshiring.
2. Sintaks xato bo'lsa — tuzating, keyin qayta tekshiring.
3. `python -m pytest tests/ --tb=short -q` ni ishga tushiring.
4. Test xatolari bo'lsa — har bir xatoni tahlil qilib, tuzating.
5. Barcha testlar o'tgach — `python manage.py check` ni ishga tushiring.
6. Natijani qisqacha xabar bering: nechta test o'tdi, nechta tuzatildi.

## Qo'shimcha
- Faqat `tests/` papkasidagi testlar ishga tushiriladi.
- Bot serverda ishlayotgan bo'lsa — `python bot/run.py` ishga tushirilmaydi.
- Migration kerak bo'lsa — foydalanuvchiga aytiladi, avtomatik bajarilamaydi.
