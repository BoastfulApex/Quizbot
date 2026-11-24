# Nomlash konventsiyalari

## Python
- Funksiyalar va o'zgaruvchilar: `snake_case`
- Klasslar: `PascalCase`
- Konstantalar: `UPPER_SNAKE_CASE`
- Private funksiyalar: `_boshlanuvchi_pastki_chiziq`

## Fayllar
- Handler fayllari: `bot/handlers/users/<ism>.py` yoki `bot/handlers/admins/<ism>.py`
- Servis fayllari: `services/<domen>_service.py`
- State fayllari: `bot/states/<ism>_states.py`
- Keyboard fayllari: `bot/keyboards/inline/<ism>_inline.py` yoki
  `bot/keyboards/default/<ism>.py`
- Test fayllari: `tests/test_<modul_nomi>.py`

## Django modellari
- Model nomi: `PascalCase` (birlik: `Quiz`, emas `Quizzes`)
- Jadval nomi: avtomatik, o'zgartirish kerak emas (agar standart bo'lsa)
- FK maydoni: `<model_nomi_kichik>` (masalan: `quiz`, `created_by`)

## Telegram tugmalar (texts.py)
- Konstantalar: `BTN_<NOM>` formatida (masalan: `BTN_MY_QUIZZES`, `BTN_SETTINGS`)
- Matn o'zgaruvchilari: `MSG_<NOM>` formatida (masalan: `MSG_WELCOME`)

## aiogram
- Router: `router = Router(name=__name__)`
- Callback data: `PascalCase` + `Callback` suffiks (masalan: `VisibilityCallback`,
  `SettingsToggleCallback`)
- Callback prefix: qisqa, noyob 2-5 belgidan iborat (masalan: `"vis"`, `"stg"`, `"qz"`)
