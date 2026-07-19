from aiogram.fsm.state import State, StatesGroup


class ImportStates(StatesGroup):
    choosing_target = State()
    new_quiz_title = State()
    new_quiz_time_per_question = State()
    new_quiz_visibility = State()
    choosing_existing_quiz = State()
    awaiting_file = State()
