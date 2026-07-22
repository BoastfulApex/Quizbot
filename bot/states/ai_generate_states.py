from aiogram.fsm.state import State, StatesGroup


class AiGenerateStates(StatesGroup):
    topic = State()
    question_count = State()
    visibility = State()
    time_per_question = State()
