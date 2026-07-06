# Skill: Django + aiogram hybrid arxitektura

Ushbu loyihada bot (aiogram, async) va web admin panel (Django, sync ORM) bitta
PostgreSQL bazani baham ko'radi. Yangi funksiya qo'shishda quyidagi patternga amal qiling.

## Standart pattern: Django ORM'ga async kirish

```python
# services/quiz_service.py
from asgiref.sync import sync_to_async
from apps.quizzes.models import Quiz
import logging

logger = logging.getLogger(__name__)

@sync_to_async
def get_quiz_by_id(quiz_id: int) -> Quiz | None:
    try:
        return Quiz.objects.select_related("created_by").get(id=quiz_id)
    except Quiz.DoesNotExist:
        return None
    except Exception:
        logger.exception("get_quiz_by_id xatosi, quiz_id=%s", quiz_id)
        return None
```

## Nima qilmaslik kerak
- Funksiya ichida `from apps.xxx.models import Yyy` yozib, keyin uni bir necha joyda
  takrorlash — bu circular import muammosini "yashiradi", asl sababni tuzatish kerak
  (odatda models.py'larni to'g'ri joylashtirish yoki `apps.py` da signal orqali).
- Bitta funksiyada bir nechta domenni aralashtirish (masalan quiz va scheduler mantiqi
  bitta funksiyada) — buni ikkita alohida servisga bo'ling.

## Django tomonda async view kerak bo'lsa
Django 5.x `async def` view'larni qo'llab-quvvatlaydi — agar web admin panelda
og'ir so'rov (masalan AI chaqiruvi) bo'lsa, `async def` view + `httpx.AsyncClient`
ishlatiladi, `sync_to_async`ni teskarisiga aylantirish shart emas.

## Migratsiyalar
Har doim `python manage.py makemigrations <app_name>` — avtomatik nom bilan emas,
aniq app nomi ko'rsatib chaqiring, keyin diff'ni ko'rib chiqing.
