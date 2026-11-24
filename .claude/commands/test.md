---
name: test
description: Testlarni ishga tushirish va natijani ko'rsatish
---

# /test buyrug'i

## Tartib
1. `python -m pytest tests/ -v --tb=short` ni ishga tushiring.
2. Muvaffaqiyatsiz testlarni sanab, har birining xato sababini ko'rsating.
3. Umumiy natija: `X passed, Y failed` formatida xabar bering.

## Parametrlar (ixtiyoriy)
- `/test <fayl>` — faqat bitta test faylini ishga tushirish:
  `python -m pytest tests/test_<fayl>.py -v --tb=short`
- `/test -q` — qisqa chiqish:
  `python -m pytest tests/ --tb=no -q`
