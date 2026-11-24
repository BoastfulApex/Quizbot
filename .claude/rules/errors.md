# Xato boshqaruvi qoidalari

## Majburiy qoidalar
- `except: pass` **TAQIQLANADI** — har doim aniq exception turi ko'rsatiladi.
- `except Exception as e: print(e)` **TAQIQLANADI** — `logging.exception(...)` ishlatiladi.
- `logging.error(...)` yoki `logging.warning(...)` emas — xato ssenariyda `logging.exception()`
  chunki u avtomatik traceback qo'shadi.

## To'g'ri pattern
```python
import logging
logger = logging.getLogger(__name__)

try:
    result = await some_service_call()
except DatabaseError:
    logger.exception("quiz_service: ma'lumot saqlashda xato, user_id=%s", user_id)
    return None
```

## Servis qaytarish qoidasi
- Muvaffaqiyatsiz holda servis `None` yoki `False` qaytaradi (hech qachon exception ko'tarmaydi
  handler'ga — faqat ichki xatolar uchun `logging.exception`).
- Handler `None` tekshirib, foydalanuvchiga mos xabar ko'rsatadi.

## Telegram xatolari
- `TelegramBadRequest` — xabar o'zgartirilmasa (masalan, kontent bir xil bo'lsa) — `pass` qilish
  mumkin, lekin `logger.debug(...)` bilan log qilinishi tavsiya etiladi.
- `TelegramForbiddenError` — bot chiqarib yuborilgan guruhni bazadan o'chirish kerak.
- Boshqa Telegram xatolari `logging.exception(...)` bilan log qilinadi.

## Validatsiya xatolari
- Foydalanuvchi kiritgan noto'g'ri qiymat uchun exception ko'tarish emas — handler ichida
  tekshiriladi va foydalanuvchiga izohli xabar yuboriladi.
