# QuizBot — loyiha konteksti

## Nima bu loyiha
Telegram test-viktorina boti (UGC model): test yaratish, Excel/CSV/DOCX/PDF/PPTX import,
AI orqali savol generatsiya, avtomatik rejalashtirish, guruhga share/unshare,
va Django asosidagi web admin panel.

## Stack
- **Bot:** Python 3.14, aiogram 3.29 (async, polling)
- **Web admin:** Django 5.2 + PostgreSQL — `apps/*/models.py` yagona manba
- **AI:** Anthropic Claude API (`claude-opus-4-8`, streaming + adaptive thinking)
- **Fayl import:** pandas, openpyxl, python-docx, pypdf, python-pptx
- **Rejalashtirish:** APScheduler 3.x
- **Test:** pytest + pytest-django (65 test, 0 xato)

## Yo'llar
| Nima | Yo'l |
|---|---|
| Kod | `D:/Python/Projects/Quizbot` |
| Vault | `D:/ObsidianVault/QuizBot` |
| Qoidalar | `.claude/rules/` |
| TZ | `docs/TZ.md` |

## Sessiya tartibi
1. Sessiya boshida `D:/ObsidianVault/QuizBot/_holat.md` ni o'qi
2. `arxiv/` ni faqat so'ralganda o'qi
3. Muhim ishdan keyin `/save` ni taklif qil
4. Arxitektura qarori bo'lsa `/decision` ni chaqir

## Muhim arxitektura qarorlari
1. **Django ORM yagona manba** — aiogram tarafida SQLAlchemy YO'Q; bot `services/*.py`
   ichida `sync_to_async` orqali Django modellariga kiradi.
2. **`services/` domen bo'yicha** — `quiz_service`, `import_service`, `ai_generator_service`,
   `share_service`, `scheduler_service`, `moderation_service`, `user_service`. God file yo'q.
3. **Egalik tekshiruvi majburiy** — yozish/o'chirish/share oldidan `created_by == user_id`
   yoki admin. `bot/middlewares/ownership_check.py` va servis darajasida markazlashgan.
4. **Share faqat test egasiga** — `group_shared_quizzes.UNIQUE(chat_id, quiz_id)`.
5. **Bot guruhga a'zo bo'lishi shart** — `/startTest` va reyting uchun.

## Kodlash konventsiyalari
- `except: pass` yoki `print(e)` **TAQIQLANADI** — doim `logging.exception(...)`.
- Har bir yangi `services/*.py` funksiyasi uchun `tests/` da mos test.
- `.bak` va commented-out bloklar commit qilinmaydi.
- Migratsiya: `python manage.py makemigrations <app>` (aniq app nomi).

## Buyruqlar
| Buyruq | Fayl | Nima qiladi |
|---|---|---|
| `/save` | `commands/save.md` | Vault'ga sessiya logi + `_holat.md` yangilash |
| `/decision` | `commands/decision.md` | `decisions/` ga arxitektura qarori yozish |
| `/fix-and-build` | `commands/fix-and-build.md` | Sintaks + testlarni tuzatish va ishga tushirish |
| `/test` | `commands/test.md` | Testlarni ishga tushirish |
| `/add-handler` | `commands/add-handler.md` | Yangi aiogram handler qo'shish |
| `/add-admin-endpoint` | `commands/add-admin-endpoint.md` | Django admin endpoint qo'shish |

## Skills
| Skill | Nima uchun |
|---|---|
| `django-aiogram-hybrid` | `sync_to_async` pattern, bitta ORM qoidasi |
| `excel-import` | Import validatsiya tartibi, ustun formati |
| `ai-generate` | Anthropic streaming + JSON parse pattern |

## Agentlar
| Agent | Vazifa |
|---|---|
| `backend-reviewer` | services/, apps/, bot/ — arxitektura va xavfsizlik ko'rib chiqish |
| `telegram-bot-architect` | Yangi bot funksiyasi loyihalashtirish |
| `reviewer` | Faqat o'qish — topilmalarni `fayl:qator + ssenariy` bilan beradi |
