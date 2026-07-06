# TEXNIK TOPSHIRIQ (TZ)

## Loyiha: QuizBot — Telegram test-viktorina boti (yaxshilangan versiya)

**Versiya:** 2.1 (Django ORM arxitekturasiga moslashtirilgan)

**Sana:** 2026-07-06

**O'zgarish tarixi:**
v1.0 — dastlabki TZ; v2.0 — UGC (har qanday user test yaratadi), guruh-share mantiqi, `/unshare` qo'shildi;
v2.1 — DB qatlami **Django ORM** ga moslashtirildi (asl v2.0 hujjatida SQLAlchemy 2.0 + Alembic ko'rsatilgan edi,
lekin loyihaning `.claude/CLAUDE.md` arxitektura qarori va mavjud skeleton — `apps/`, `core/`, `manage.py` —
Django ORM'ni yagona manba sifatida belgilagan; shuning uchun bo'lim 3 va 8 shu hujjatda Django'ga moslab
yangilangan, qolgan barcha funksional talablar o'zgarishsiz saqlangan).

---

## 1. Loyiha maqsadi

Mavjud QuizBot'ning funksional cheklovlarini bartaraf etuvchi, savol bazasini tezkor to'ldirish, testlarni avtomatik rejalashtirish va sun'iy intellekt (AI) yordamida istalgan mavzu bo'yicha savollar generatsiya qilish imkoniyatiga ega, **har qanday foydalanuvchi o'z testini yarata oladigan** Telegram bot yaratish.

## 2. Hal qilinadigan muammolar (mavjud tizimdagi kamchiliklar)

| # | Muammo | Yechim |
|---|---|---|
| 1 | Savollarni Excel/CSV'dan ommaviy import qilib bo'lmaydi | `.xlsx` / `.csv` fayldan avtomatik import moduli |
| 2 | 1000+ savolni qo'lda kiritish vaqt oladi | Ommaviy import + AI orqali avtomatik generatsiya |
| 3 | Testlarni avtomatik rejalashtirish yo'q | Cron-asosli scheduler (bir martalik va takrorlanuvchi) |
| 4 | Share tugmasini o'chirib bo'lmaydi | Foydalanuvchi/admin darajasidagi sozlama |
| 5 | Faqat admin test yarata oladi | **Har qanday foydalanuvchi** test yarata oladi (UGC model) |
| 6 | Mavzu bo'yicha savol yo'q | Claude API orqali istalgan mavzudan savol generatsiyasi |

## 3. Texnologik stack (v2.1 — Django ORM'ga moslashtirilgan)

- **Til/Framework (bot):** Python 3.12, aiogram 3.x (async, polling)
- **Web admin panel:** Django 5.x — bot bilan **bitta umumiy PostgreSQL** bazani ishlatadi
- **Baza:** PostgreSQL 16, **Django ORM** (yagona manba, `apps/*/models.py`) —
  aiogram tomonida SQLAlchemy YOZILMAYDI, bot `sync_to_async` orqali Django modellariga kiradi
  (`services/*.py` ichida). Migratsiyalar — `python manage.py makemigrations/migrate` (Alembic emas)
- **Fayl bilan ishlash:** pandas, openpyxl (Excel), csv (standart kutubxona)
- **Rejalashtirish:** APScheduler (kelajakda yuklama oshsa — Celery + Redis)
- **AI:** Anthropic Claude API (model: claude-sonnet-5)
- **Konteynerlash:** Docker, docker-compose
- **Loglash:** Python logging + (ixtiyoriy) Sentry
- **Muhit boshqaruvi:** `.env` + pydantic-settings (Django tomonida `core/settings.py` orqali o'qiladi)

## 4. Foydalanuvchi rollari

1. **Super Admin** — botni to'liq boshqaradi, adminlarni tayinlaydi, barcha testlarni moderatsiya qiladi
2. **Admin** — barcha testlarni ko'radi/o'chiradi, global sozlamalarni boshqaradi, foydalanuvchilarni bloklaydi, istalgan guruhga istalgan testni ulashtira oladi
3. **Foydalanuvchi (User)** — o'z testini yaratadi (qo'lda/import/AI orqali), **faqat o'zi yaratgan testni** guruhga ulashtira oladi, rejalashtira oladi; boshqa (ommaviy) testlarni ishlaydi, natijalarini ko'radi, sozlamalarni boshqaradi

> **Asosiy tamoyil:** Bot "admin boshqaruvidagi" emas, balki **user-generated content (UGC)** platformasi. Har bir test **bitta egaga** tegishli (`created_by`), va faqat egasi (yoki Admin) uni tahrirlashi, o'chirishi, guruhga ulashtirishi yoki guruhdan olib tashlashi mumkin.

## 5. Funksional talablar

### 5.1 Ro'yxatdan o'tish va asosiy menyu

- `/start` — botni ishga tushirish, foydalanuvchini bazaga qo'shish
- `/help` — buyruqlar ro'yxati
- Asosiy menyu: Test yaratish | Test boshlash | Mening testlarim | Reyting | Sozlamalar | (Admin bo'lsa) Admin panel

### 5.2 Test yaratish va boshqarish (Har qanday foydalanuvchi)

- `/newquiz` — yangi test (kategoriya, sarlavha, tavsif, qiyinlik darajasi)
- Test yaratuvchisi (`created_by`) avtomatik saqlanadi — faqat egasi (yoki admin) uni tahrirlashi/o'chirishi mumkin
- Test ko'rinishi tanlanadi:
  - **Shaxsiy (private)** — faqat yaratuvchi va u ulashgan guruh/link orqali kirganlar ko'radi
  - **Ommaviy (public)** — bot ichidagi umumiy test katalogida barcha foydalanuvchilarga ko'rinadi
- Savol qo'shish: qo'lda (matn + 4 variant + to'g'ri javob + izoh) yoki quyidagi usullar orqali:

#### 5.2.1 Excel/CSV import

- `/import` buyrug'i → foydalanuvchi faylni yuboradi
- Kutilgan format (ustunlar): `savol | variant_a | variant_b | variant_c | variant_d | togri_javob | izoh | qiyinlik`
- Bot validatsiya qiladi: bo'sh maydonlar, noto'g'ri javob belgisi, dublikatlar
- Natija hisoboti: "✅ 950 ta savol qo'shildi / ❌ 12 tasi xato (qator raqamlari va sabab ko'rsatiladi)"
- Xato qatorlar uchun tuzatilgan faylni qayta yuklash imkoniyati
- Katta fayllar (1000+ qator) uchun asinxron background ishlov berish, progress-bar xabari
- **Cheklov:** foydalanuvchi boshiga kunlik import limiti (masalan, kuniga 3 ta fayl / 5000 qatorgacha), limit admin panelda sozlanadi

#### 5.2.2 AI orqali mavzudan savol generatsiya qilish

- `/generate` buyrug'i → foydalanuvchi mavzuni kiritadi (masalan: "Amir Temur davri")
- Bot quyidagilarni so'raydi: savollar soni (10/20/50), qiyinlik darajasi, til
- Claude API'ga structured JSON formatda so'rov yuboriladi
- Qaytgan savollar foydalanuvchiga preview sifatida ko'rsatiladi (tasdiqlash/tahrirlash/rad etish)
- Tasdiqlangan savollar avtomatik bazaga saqlanadi va mavjud yoki yangi test kategoriyasiga biriktiriladi
- **Cheklov:** foydalanuvchi boshiga kunlik/oylik generatsiya limiti (masalan, kuniga 50 ta savolgacha bepul), limitdan tashqarisi kelajakda premium tarif orqali ochilishi mumkin (v3.0)

### 5.3 Test tanlash va boshlash oqimi (`/startTest`)

Bot chaqirilgan **kontekstga** (shaxsiy chat yoki guruh) qarab turlicha ishlaydi:

**A) Shaxsiy chatda:**
- Bot foydalanuvchiga tegishli (o'zi yaratgan + ommaviy katalogdagi) testlar ro'yxatini inline keyboard shaklida ko'rsatadi, yoki kategoriya bo'yicha filtrlaydi (testlar ko'p bo'lsa)
- `/startTest <nom yoki ID>` — aniq moslik topilsa darhol boshlanadi, bir nechta moslik bo'lsa ro'yxat chiqadi

**B) Guruhda:**

Bot guruhga ulashilgan testlar ro'yxatini (`group_shared_quizzes` jadvali) tekshiradi:

| Holat | Bot xatti-harakati |
|---|---|
| Guruhga 1 ta test ulashilgan | O'sha test darhol, tanlovsiz boshlanadi |
| Guruhga 2+ ta test ulashilgan | "Qaysi testni boshlaymiz?" — inline tugmalar bilan ro'yxat ko'rsatiladi |
| Guruhga hech narsa ulashilmagan | Xabar: "Bu guruhda test ulashilmagan. Shaxsiy chatda test tanlang yoki ulashing" |

**C) Deep link orqali:** `https://t.me/QuizBot?start=quiz_42` — link bosilganda o'sha test (ID=42) to'g'ridan-to'g'ri, hech qanday tanlovsiz boshlanadi (shaxsiy chatda ochiladi)

### 5.4 Ulashish (Share) va guruh testlari

#### 5.4.1 Share huquqi

- **Faqat testning egasi** (`created_by`) yoki Admin uni guruhga ulashtira oladi
- Boshqa foydalanuvchi (test muallifi bo'lmagan, hatto uni ishlagan bo'lsa ham) Share tugmasini bossa: `❌ Faqat test muallifi buni guruhga ulashishi mumkin`

#### 5.4.2 Bot guruhga qo'shilishi talabi

- Guruh ichida `/startTest`, umumiy reyting va savol-javoblarni to'g'ridan-to'g'ri guruh chatida ko'rsatish uchun **bot o'sha guruhga a'zo (yoki admin) sifatida qo'shilgan bo'lishi shart** — bu Telegram Bot API cheklovi (bot faqat o'zi a'zo bo'lgan chatlarga xabar yuborishi/qabul qilishi mumkin)
- Agar bot guruhda bo'lmasa, Share bosilganda bot: "Botni avval guruhga qo'shing" xabarini va bot-ni guruhga qo'shish tugmasini (`add_to_group` deep link) ko'rsatadi

#### 5.4.3 Share jarayoni

```
Egasi (shaxsiy chatda): [Share] tugmasini bosadi → guruhni tanlaydi (bot allaqachon a'zo bo'lgan guruhlar ro'yxatidan)
→ Bot guruhga xabar yuboradi: "🎯 [Test nomi] ulashildi. Boshlash uchun /startTest"
→ group_shared_quizzes jadvaliga yozuv qo'shiladi
```

- `UNIQUE(chat_id, quiz_id)` — bitta test bitta guruhga faqat bir marta yozuv sifatida saqlanadi (qayta ulashilsa, mavjud yozuv yangilanadi/faollashtiriladi)

#### 5.4.4 `/unshare`

- `/unshare` buyrug'i guruhda chaqiriladi
- Bot **shu foydalanuvchi ulashgan** testlar ro'yxatini ko'rsatadi (yoki Admin bo'lsa — guruhdagi barcha ulashilgan testlarni)
- Tanlangan test uchun `group_shared_quizzes.is_active = false`, `unshared_at`, `unshared_by` yoziladi (yozuv o'chirilmaydi — tarix saqlanadi)
- Faqat **shared_by == foydalanuvchi** yoki Admin bu amalni bajara oladi

#### 5.4.5 Share tugmasini butunlay o'chirish (sozlama)

- `/settings` orqali foydalanuvchi o'z testlari uchun Share tugmasini yashira oladi (hech kim, hatto o'zi ham vaqtincha ulashmasin desa)
- Admin darajasida global sozlash: butun bot uchun Share funksiyasini yoqish/o'chirish

### 5.5 Testlarni rejalashtirish (Scheduler)

- `/schedule` buyrug'i → foydalanuvchi **o'ziga tegishli** testni tanlaydi
- Rejalashtirish turlari: bir martalik (aniq sana/vaqt) yoki takrorlanuvchi (cron: kunlik/haftalik/oylik)
- Yuborish manzili:
  - Oddiy foydalanuvchi → faqat bot a'zo bo'lgan va o'zi test egasi/ulashgan guruhlarga
  - Admin → istalgan guruh/kanal yoki barcha faol foydalanuvchilarga
- `/schedules` — foydalanuvchining o'z rejalarini ko'rish, tahrirlash, bekor qilish

### 5.6 Test ishlash jarayoni

- Har bir savol uchun vaqt cheklovi (sozlanadigan, masalan 30 soniya)
- Javob berilgach — to'g'ri/noto'g'ri, izoh ko'rsatiladi
- Yakunda: ball, to'g'ri/noto'g'ri javoblar soni, sarflangan vaqt, Share tugmasi (agar yoqilgan bo'lsa)

### 5.7 Reyting va statistika

- `/leaderboard` — umumiy yoki test bo'yicha top-foydalanuvchilar (shaxsiy va guruh darajasida alohida)
- Foydalanuvchi profili: umumiy ball, ishlangan/yaratgan testlar soni, aniqlik foizi

### 5.8 Admin panel

- Statistika: faol foydalanuvchilar, eng mashhur/eng ko'p ulashilgan testlar, kunlik faollik
- Foydalanuvchilarni boshqarish (bloklash, admin qilish)
- Barcha foydalanuvchi testlarini ko'rish/o'chirish/nofaollashtirish (moderatsiya)
- Bu funksiyalar **ikki qatlamda** taqdim etiladi: (1) bot ichidagi `/admin` buyruqlari orqali tezkor amallar,
  (2) Django web admin panel (`apps/*/admin.py` — ModelAdmin) orqali batafsil ko'rish/CRUD. Ikkalasi ham
  bir xil Django modellariga tayanadi, mantiq takrorlanmaydi.

### 5.9 Kontent moderatsiyasi

- `/report` — foydalanuvchi nomaqbul testni admin'ga xabar qilishi
- Import/AI-generatsiya natijalari avtomatik so'z-filtridan o'tadi
- (Ixtiyoriy sozlama) Yangi ommaviy testlar admin tasdiqlagandan keyin katalogda ko'rinadi
- Bloklangan foydalanuvchining barcha ommaviy testlari va guruh share'lari avtomatik yashiriladi

## 6. Ma'lumotlar bazasi tuzilishi (asosiy jadvallar, Django modellari sifatida)

Quyidagi jadvallar `apps/users`, `apps/quizzes`, `apps/moderation` orasida taqsimlanadi
(aniq taqsimot — reja bosqichida belgilanadi):

```
users                 (id, telegram_id, username, role, is_blocked, created_at)
user_settings         (user_id, hide_share_button, notifications_on, language)
quizzes               (id, title, description, category, difficulty, created_by,
                       is_active, visibility ['private'|'public'],
                       source ['manual'|'import'|'ai'], moderation_status, created_at)
questions             (id, quiz_id, question_text, option_a, option_b, option_c, option_d,
                       correct_option, explanation, difficulty)
quiz_sessions         (id, quiz_id, user_id, chat_id, score, started_at, finished_at)
answers               (id, session_id, question_id, selected_option, is_correct, time_taken_sec)
group_shared_quizzes  (id, chat_id, quiz_id, shared_by, shared_at,
                       is_active, unshared_at, unshared_by,
                       UNIQUE(chat_id, quiz_id))
schedules             (id, quiz_id, cron_expression, run_once_at, target_chat_id,
                       is_active, created_by)
import_logs           (id, user_id, filename, total_rows, success_count,
                       error_count, error_details_json, created_at)
ai_generation_logs    (id, user_id, topic, questions_count, model_used, created_at)
reports               (id, quiz_id, reported_by, reason, status, created_at)
```

Migratsiyalar: `python manage.py makemigrations <app_nomi>` orqali (qo'lda migratsiya fayli yozilmaydi).

## 7. Nofunksional talablar

- **Ishlash tezligi:** 1000 qatorli faylni 30 soniyadan kam vaqtda import qilish
- **Xavfsizlik:**
  - Admin-darajasidagi amallar (boshqa userning testini o'chirish, global sozlash) faqat tasdiqlangan `telegram_id` uchun ochiq
  - Oddiy foydalanuvchi faqat **o'z testlarini** boshqaradi va **faqat o'zi ulashgan** guruh-testlarini unshare qila oladi (`created_by` / `shared_by` bo'yicha tekshiruv)
  - Bot guruh a'zoligi Telegram Bot API orqali tekshiriladi — a'zo bo'lmagan guruhga xabar yuborish urinishi rad etiladi
- **Suiiste'molni cheklash:** import va AI-generatsiya uchun kunlik limitlar (rate limiting)
- **Kengaytiriluvchanlik:** yangi til yoki AI provayder qo'shish oson bo'lishi uchun servis qatlamlari alohida ajratilgan
- **Zaxira nusxalash:** PostgreSQL uchun kunlik avtomatik backup
- **Loglash:** import, AI generatsiya, share/unshare amallari log qilinadi (`logging.exception`, `print()` taqiqlangan)

## 8. Loyiha strukturasi (v2.1 — mavjud skeletonga mos)

```
quizbot/
├── apps/                         # Django apps — modellar yagona manba
│   ├── users/                    # User, UserSettings, role/is_blocked
│   ├── quizzes/                  # Quiz, Question, QuizSession, Answer,
│   │                             # GroupSharedQuiz, Schedule
│   └── moderation/                # ImportLog, AiGenerationLog, Report
├── core/                         # Django project (settings, urls, asgi/wsgi)
├── bot/
│   ├── handlers/
│   │   ├── users/
│   │   │   ├── start.py
│   │   │   ├── quiz.py              # /startTest, test ishlash
│   │   │   ├── quiz_create.py       # /newquiz, savol qo'shish
│   │   │   ├── import_handler.py    # /import
│   │   │   ├── ai_generate.py       # /generate
│   │   │   ├── share_handler.py     # Share / /unshare
│   │   │   ├── schedule_handler.py  # /schedule, /schedules
│   │   │   └── report.py            # /report
│   │   ├── admins/
│   │   │   └── admin.py
│   │   └── errors/
│   │       └── error_handler.py
│   ├── middlewares/
│   │   ├── admin_check.py
│   │   ├── ownership_check.py   # created_by / shared_by tekshiruvi
│   │   └── rate_limit.py
│   ├── filters/
│   ├── keyboards/
│   ├── states/
│   ├── loader.py
│   └── run.py
├── services/                     # domen bo'yicha ajratilgan, Django ORM'ga sync_to_async orqali kiradi
│   ├── quiz_service.py
│   ├── import_service.py
│   ├── ai_generator_service.py
│   ├── share_service.py
│   ├── scheduler_service.py
│   └── moderation_service.py
├── data/
│   └── config.py                 # pydantic-settings orqali .env o'qiladi
├── locales/
├── tests/
├── docker-compose.yml
├── requirements.txt
├── manage.py
├── .env.example
└── README.md
```

## 9. Ishlab chiqish bosqichlari (taxminiy)

| Bosqich | Ish | Muddat |
|---|---|---|
| 1 | Loyiha skeleti, baza modellari (Django), Docker sozlash | 2-3 kun |
| 2 | Asosiy bot funksiyalari (ro'yxatdan o'tish, test yaratish, ishlash) | 4-5 kun |
| 3 | Excel/CSV import moduli | 2-3 kun |
| 4 | AI orqali savol generatsiya moduli | 2-3 kun |
| 5 | Share / Unshare / guruh-share mantiqi | 3-4 kun |
| 6 | Rejalashtirish (scheduler) moduli | 2 kun |
| 7 | Reyting, admin panel, moderatsiya | 3 kun |
| 8 | Testlash, xatolarni tuzatish, deploy | 2-3 kun |

**Umumiy taxminiy muddat:** 20-26 ish kuni (1 dasturchi uchun)

## 10. Kelajakda kengaytirish imkoniyatlari (v3.0 uchun)

- Ko'p tilli interfeys (o'zbek, rus, ingliz)
- Guruh musobaqasi rejimi (real-time, umumiy vaqt, jonli reyting)
- To'lov tizimi integratsiyasi (premium: yuqori import/AI limitlari)
- Web admin-panel (Telegram tashqarisida) — **eslatma:** bu allaqachon Django orqali rejalashtirilgan (bo'lim 3),
  v3.0 kengaytmasi undan tashqari alohida frontend (masalan, React) qo'shishni nazarda tutadi
- Rasm/audio bilan savollar

---

*Ushbu hujjat loyihaning TZ hisoblanadi va ishlab chiqish jarayonida aniqlashtirilishi mumkin.*
