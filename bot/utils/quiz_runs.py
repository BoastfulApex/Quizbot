from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


@dataclass
class QuizRun:
    chat_id: int
    quiz_id: int
    quiz_title: str
    initiator_telegram_id: int
    time_per_question_sec: int
    total_questions: int
    current_index: int = 0
    poll_id_to_question_id: dict[str, int] = field(default_factory=dict)
    participants: dict[int, tuple[int, str]] = field(default_factory=dict)
    task: asyncio.Task | None = None
    stopped: bool = False


_active_runs: dict[int, QuizRun] = {}


def get_run(chat_id: int) -> QuizRun | None:
    return _active_runs.get(chat_id)


def register_run(run: QuizRun) -> None:
    _active_runs[run.chat_id] = run


def pop_run(chat_id: int) -> QuizRun | None:
    return _active_runs.pop(chat_id, None)


def iter_runs() -> list[QuizRun]:
    return list(_active_runs.values())
