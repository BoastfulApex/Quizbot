from aiogram.fsm.state import State, StatesGroup


class QuizCreateStates(StatesGroup):
    title = State()
    description = State()
    category = State()
    difficulty = State()
    visibility = State()
    time_per_question = State()
    question_text = State()
    question_option_a = State()
    question_option_b = State()
    question_option_c = State()
    question_option_d = State()
    question_correct = State()
    question_explanation = State()
    confirm_add_more = State()


class QuizSelectStates(StatesGroup):
    choosing_quiz = State()


class QuizReadyStates(StatesGroup):
    confirming = State()
