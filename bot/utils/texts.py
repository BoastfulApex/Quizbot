WELCOME_TEXT = (
    "👋 Assalomu alaykum, {name}!\n\n"
    "<b>QuizBot</b> — test-viktorina boti. Quyidagi menyu orqali botning "
    "imkoniyatlaridan foydalanishingiz mumkin:\n\n"
    "📝 <b>Test yaratish</b> — o'z testingizni yaratish (qo'lda, Excel/CSV import yoki AI orqali)\n"
    "▶️ <b>Test boshlash</b> — mavjud testlardan birini ishlash\n"
    "📂 <b>Mening testlarim</b> — o'zingiz yaratgan testlarni ko'rish/boshqarish\n"
    "🏆 <b>Reyting</b> — eng yaxshi natijalar\n"
    "⚙️ <b>Sozlamalar</b> — bot sozlamalarini boshqarish\n\n"
    "Barcha buyruqlar ro'yxati uchun /help yuboring."
)

HELP_TEXT = (
    "<b>QuizBot buyruqlari:</b>\n\n"
    "/start — botni ishga tushirish va asosiy menyuni ko'rsatish\n"
    "/help — ushbu yordam xabari\n"
    "/newquiz — yangi test yaratish (qo'lda / import / AI)\n"
    "/import — Excel yoki CSV fayldan savollarni import qilish\n"
    "/generate — AI yordamida mavzu bo'yicha savollar generatsiya qilish\n"
    "/startTest — testni boshlash (shaxsiy chat yoki guruhga qarab)\n"
    "/schedule — testni rejalashtirish (bir martalik yoki takrorlanuvchi)\n"
    "/schedules — o'z rejalaringizni ko'rish/boshqarish\n"
    "/leaderboard — reyting jadvali\n"
    "/settings — shaxsiy sozlamalar\n"
    "/report — nomaqbul testni admin'ga xabar qilish\n"
    "/unshare — guruhda ulashilgan testni bekor qilish (faqat guruh ichida)\n"
    "/admin — admin panel (faqat admin/super admin uchun)\n\n"
    "⚠️ Ba'zi funksiyalar hozircha ishlab chiqilmoqda — mos menyu tugmasini bosganda "
    "qisqa tushuntirish beriladi."
)

GUIDE_CREATE_QUIZ = (
    "📝 <b>Test yaratish</b>\n\n"
    "Test yaratishning uchta usuli bo'ladi:\n"
    "1️⃣ Qo'lda — savol, 4 variant, to'g'ri javob va izoh kiritish\n"
    "2️⃣ Import — Excel/CSV fayldan ommaviy yuklash (/import)\n"
    "3️⃣ AI — mavzuni yozsangiz, savollar avtomatik generatsiya qilinadi (/generate)\n\n"
    "🚧 Bu funksiya tez orada ishga tushadi."
)

GUIDE_START_TEST = (
    "▶️ <b>Test boshlash</b>\n\n"
    "Shaxsiy chatda o'zingiz yaratgan yoki ommaviy katalogdagi testlar ro'yxatidan "
    "birini tanlaysiz. Guruhda esa o'sha guruhga ulashilgan testlar orasidan tanlanadi "
    "yoki bitta test bo'lsa darhol boshlanadi.\n\n"
    "🚧 Bu funksiya tez orada ishga tushadi."
)

GUIDE_MY_QUIZZES = (
    "📂 <b>Mening testlarim</b>\n\n"
    "Bu bo'limda siz yaratgan barcha testlarni ko'rasiz: tahrirlash, o'chirish, "
    "guruhga ulashish yoki rejalashtirish imkoniyati bilan.\n\n"
    "🚧 Bu funksiya tez orada ishga tushadi."
)

GUIDE_LEADERBOARD = (
    "🏆 <b>Reyting</b>\n\n"
    "Umumiy yoki test bo'yicha eng yaxshi natijalar ro'yxati — shaxsiy va guruh "
    "darajasida alohida ko'rsatiladi.\n\n"
    "🚧 Bu funksiya tez orada ishga tushadi."
)

GUIDE_SETTINGS = (
    "⚙️ <b>Sozlamalar</b>\n\n"
    "Bu yerda Share tugmasini yashirish, bildirishnomalarni yoqish/o'chirish va "
    "interfeys tilini tanlash imkoniyati bo'ladi.\n\n"
    "🚧 Bu funksiya tez orada ishga tushadi."
)

GUIDE_ADMIN_PANEL = (
    "🛠 <b>Admin panel</b>\n\n"
    "Statistika, foydalanuvchilarni boshqarish (bloklash/admin qilish) va "
    "testlarni moderatsiya qilish shu yerda bo'ladi.\n\n"
    "🚧 Bu funksiya tez orada ishga tushadi."
)
