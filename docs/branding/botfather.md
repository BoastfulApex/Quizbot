# Savolgo — BotFather sozlamalari

Rasmlar `python docs/branding/make_icon.py` bilan qayta yaratiladi.

| Buyruq | Qiymat |
|---|---|
| `/setname` | `Savolgo — Test va Viktorina` |
| `/setuserpic` | `docs/branding/savolgo_avatar.png` (640×640) |
| `/setdescriptionpic` | `docs/branding/savolgo_description.png` (640×360) |
| `/setabouttext` | quyidagi "About" matni (≤120 belgi) |
| `/setdescription` | quyidagi "Description" matni (≤512 belgi) |
| `/setcommands` | quyidagi buyruqlar ro'yxati |

## About (profildagi qisqa matn, 60 belgi)

```
Test yarating, AI bilan savol tuzing va guruhda bellashing 🧠
```

## Description (bot ochilganda, "Start" dan oldin ko'rinadi, 326 belgi)

```
Savolgo — test va viktorinalar boti 🧠

📝 Testni qo'lda, Excel/CSV fayldan yoki AI yordamida yarating
📄 Word, PDF va PowerPoint hujjatlardan avtomatik savollar
👥 Guruhda do'stlaringiz bilan bellashing
🏆 Natijalar va reyting
📤 Testlarni ulashing yoki Word/Excel fayl qilib yuklab oling

Boshlash uchun «Start» tugmasini bosing 👇
```

## Commands

```
start - Botni ishga tushirish
newquiz - Yangi test yaratish
generate - AI yordamida savollar yaratish
import - Excel/CSV fayldan import
starttest - Testni boshlash
help - Yordam
```

## /start xabari

Bot `/start` da `bot/assets/welcome.png` (1280×720) rasmini `bot/utils/texts.py`
dagi `WELCOME_TEXT` bilan birga yuboradi.
