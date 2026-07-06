from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_CREATE_QUIZ = "📝 Test yaratish"
BTN_START_TEST = "▶️ Test boshlash"
BTN_MY_QUIZZES = "📂 Mening testlarim"
BTN_LEADERBOARD = "🏆 Reyting"
BTN_SETTINGS = "⚙️ Sozlamalar"
BTN_ADMIN_PANEL = "🛠 Admin panel"


def get_main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=BTN_CREATE_QUIZ), KeyboardButton(text=BTN_START_TEST)],
        [KeyboardButton(text=BTN_MY_QUIZZES), KeyboardButton(text=BTN_LEADERBOARD)],
        [KeyboardButton(text=BTN_SETTINGS)],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=BTN_ADMIN_PANEL)])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
