# Baza va xato boshqaruvi qoidalari

- Django ORM — yagona manba. aiogram tarafida yangi SQLAlchemy modeli **hech qachon**
  yaratilmaydi; barcha DB kirish `apps/*/models.py`dagi Django modellari orqali,
  `sync_to_async` bilan o'ralgan holda amalga oshiriladi.
- Har bir yangi migratsiya `python manage.py makemigrations` orqali yaratiladi va
  `apps/<app>/migrations/` ga commit qilinadi — qo'lda migratsiya fayli yozilmaydi.
- Exception handling:
  - `except: pass` yoki `except: return None` **taqiqlanadi**.
  - Har doim aniq exception turi ushlanadi va `logging.exception("...")` orqali log qilinadi.
  - `print()` orqali xato chiqarish ISHLATILMAYDI (production loglarda ko'rinmaydi).
- Har bir yangi `services/*.py` funksiyasi uchun `tests/test_*.py` da kamida bitta
  muvaffaqiyatli va bitta xato holati testi yozilishi kutiladi.
- Bitta faylga (masalan `services/quiz_service.py`) tegishli bo'lmagan domenning
  funksiyasini qo'shmang — har bir servis faqat o'z domenidagi mantiqqa javobgar
  ("god file" qilinmasin).
