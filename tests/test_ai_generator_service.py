import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.moderation.models import AiGenerationLog
from apps.users.models import User
from services.ai_generator_service import create_ai_log, generate_questions


@pytest.fixture
def user(db):
    return User.objects.create(telegram_id=20, username="ai_tester")


# --- create_ai_log ---

@pytest.mark.django_db(transaction=True)
def test_create_ai_log_success(user):
    log = asyncio.run(create_ai_log(user_id=user.id, topic="Matematika", questions_count=10))

    assert log is not None
    assert log.user_id == user.id
    assert log.topic == "Matematika"
    assert log.questions_count == 10
    assert log.model_used != ""


@pytest.mark.django_db(transaction=True)
def test_create_ai_log_returns_none_for_missing_user():
    result = asyncio.run(create_ai_log(user_id=999999, topic="Test", questions_count=5))

    assert result is None


# --- generate_questions ---

def _make_mock_message(questions: list[dict]):
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = json.dumps(questions, ensure_ascii=False)

    thinking_block = MagicMock()
    thinking_block.type = "thinking"

    mock_message = MagicMock()
    mock_message.content = [thinking_block, text_block]
    return mock_message


def _make_mock_stream(mock_message):
    mock_stream = AsyncMock()
    mock_stream.get_final_message = AsyncMock(return_value=mock_message)
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=None)
    return mock_stream


_SAMPLE_QUESTIONS = [
    {
        "question": "O'zbekistonning poytaxti qaysi shahar?",
        "option_a": "Samarqand",
        "option_b": "Buxoro",
        "option_c": "Toshkent",
        "option_d": "Andijon",
        "correct_option": "C",
        "explanation": "Toshkent O'zbekistonning poytaxti hisoblanadi.",
    },
    {
        "question": "2 + 2 = ?",
        "option_a": "3",
        "option_b": "4",
        "option_c": "5",
        "option_d": "6",
        "correct_option": "B",
        "explanation": "",
    },
]


def test_generate_questions_returns_valid_list():
    mock_message = _make_mock_message(_SAMPLE_QUESTIONS)
    mock_stream = _make_mock_stream(mock_message)

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream

    with patch("services.ai_generator_service.anthropic.AsyncAnthropic", return_value=mock_client):
        result = asyncio.run(generate_questions(topic="Geografiya", count=2))

    assert len(result) == 2
    assert result[0]["question_text"] == "O'zbekistonning poytaxti qaysi shahar?"
    assert result[0]["correct_option"] == "C"
    assert result[1]["correct_option"] == "B"
    assert result[1]["explanation"] == ""
    assert "difficulty" in result[0]


def test_generate_questions_skips_invalid_correct_option():
    bad_questions = [
        {
            "question": "Savol?",
            "option_a": "A",
            "option_b": "B",
            "option_c": "C",
            "option_d": "D",
            "correct_option": "E",
            "explanation": "",
        }
    ]
    mock_message = _make_mock_message(bad_questions)
    mock_stream = _make_mock_stream(mock_message)
    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream

    with patch("services.ai_generator_service.anthropic.AsyncAnthropic", return_value=mock_client):
        result = asyncio.run(generate_questions(topic="Test", count=1))

    assert result == []


def test_generate_questions_skips_empty_question():
    bad_questions = [
        {
            "question": "",
            "option_a": "A",
            "option_b": "B",
            "option_c": "C",
            "option_d": "D",
            "correct_option": "A",
            "explanation": "",
        }
    ]
    mock_message = _make_mock_message(bad_questions)
    mock_stream = _make_mock_stream(mock_message)
    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream

    with patch("services.ai_generator_service.anthropic.AsyncAnthropic", return_value=mock_client):
        result = asyncio.run(generate_questions(topic="Test", count=1))

    assert result == []


def test_generate_questions_truncates_long_fields():
    long_questions = [
        {
            "question": "x" * 300,
            "option_a": "y" * 150,
            "option_b": "B",
            "option_c": "C",
            "option_d": "D",
            "correct_option": "A",
            "explanation": "z" * 250,
        }
    ]
    mock_message = _make_mock_message(long_questions)
    mock_stream = _make_mock_stream(mock_message)
    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream

    with patch("services.ai_generator_service.anthropic.AsyncAnthropic", return_value=mock_client):
        result = asyncio.run(generate_questions(topic="Test", count=1))

    assert len(result) == 1
    assert len(result[0]["question_text"]) == 250
    assert len(result[0]["option_a"]) == 100
    assert len(result[0]["explanation"]) == 200


def test_generate_questions_returns_empty_on_empty_text():
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = ""

    mock_message = MagicMock()
    mock_message.content = [text_block]

    mock_stream = _make_mock_stream(mock_message)
    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream

    with patch("services.ai_generator_service.anthropic.AsyncAnthropic", return_value=mock_client):
        result = asyncio.run(generate_questions(topic="Test", count=5))

    assert result == []


def test_generate_questions_returns_empty_on_invalid_json():
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "[not valid json"

    mock_message = MagicMock()
    mock_message.content = [text_block]

    mock_stream = _make_mock_stream(mock_message)
    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream

    with patch("services.ai_generator_service.anthropic.AsyncAnthropic", return_value=mock_client):
        result = asyncio.run(generate_questions(topic="Test", count=5))

    assert result == []
