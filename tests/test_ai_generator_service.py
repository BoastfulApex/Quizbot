import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import errors as genai_errors

from apps.moderation.models import AiGenerationLog, AiProviderSettings
from apps.users.models import User
from services.ai_generator_service import create_ai_log, generate_questions, generate_questions_detailed


@pytest.fixture
def user(db):
    return User.objects.create(telegram_id=20, username="ai_tester")


@pytest.fixture
def gemini_settings(db):
    s = AiProviderSettings.load()
    s.active_provider = AiProviderSettings.Provider.GEMINI
    s.gemini_api_key = "test-gemini-key"
    s.gemini_model = "gemini-2.0-flash"
    s.save()
    return s


# --- create_ai_log ---

@pytest.mark.django_db(transaction=True)
def test_create_ai_log_success(user, gemini_settings):
    log = asyncio.run(create_ai_log(user_id=user.id, topic="Matematika", questions_count=10))

    assert log is not None
    assert log.user_id == user.id
    assert log.topic == "Matematika"
    assert log.questions_count == 10
    assert "gemini" in log.model_used


@pytest.mark.django_db(transaction=True)
def test_create_ai_log_returns_none_for_missing_user(gemini_settings):
    result = asyncio.run(create_ai_log(user_id=999999, topic="Test", questions_count=5))
    assert result is None


# --- generate_questions helpers ---

def _make_mock_gemini_client(questions: list[dict]):
    mock_response = MagicMock()
    mock_response.text = json.dumps(questions, ensure_ascii=False)
    mock_client = MagicMock()
    mock_client.aio = MagicMock()
    mock_client.aio.models = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    return mock_client


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


@pytest.mark.django_db(transaction=True)
def test_generate_questions_returns_valid_list(gemini_settings):
    mock_client = _make_mock_gemini_client(_SAMPLE_QUESTIONS)

    with patch("services.ai_generator_service.genai.Client", return_value=mock_client):
        result = asyncio.run(generate_questions(topic="Geografiya", count=2))

    assert len(result) == 2
    assert result[0]["question_text"] == "O'zbekistonning poytaxti qaysi shahar?"
    assert result[0]["correct_option"] == "C"
    assert result[1]["correct_option"] == "B"
    assert result[1]["explanation"] == ""
    assert "difficulty" in result[0]


@pytest.mark.django_db(transaction=True)
def test_generate_questions_falls_back_on_503(gemini_settings):
    mock_client = _make_mock_gemini_client(_SAMPLE_QUESTIONS)
    ok_response = mock_client.aio.models.generate_content.return_value
    busy = genai_errors.ServerError(503, {"error": {"code": 503, "message": "busy", "status": "UNAVAILABLE"}})
    mock_client.aio.models.generate_content = AsyncMock(side_effect=[busy, ok_response])

    with patch("services.ai_generator_service.genai.Client", return_value=mock_client):
        result = asyncio.run(generate_questions(topic="Geografiya", count=2))

    assert len(result) == 2
    calls = mock_client.aio.models.generate_content.call_args_list
    assert calls[0].kwargs["model"] == "gemini-2.0-flash"
    assert calls[1].kwargs["model"] == "gemini-flash-latest"


@pytest.mark.django_db(transaction=True)
def test_generate_questions_does_not_fall_back_on_auth_error(gemini_settings):
    mock_client = _make_mock_gemini_client(_SAMPLE_QUESTIONS)
    denied = genai_errors.ClientError(401, {"error": {"code": 401, "message": "bad key", "status": "UNAUTHENTICATED"}})
    mock_client.aio.models.generate_content = AsyncMock(side_effect=denied)

    with patch("services.ai_generator_service.genai.Client", return_value=mock_client):
        with pytest.raises(genai_errors.ClientError):
            asyncio.run(generate_questions(topic="Geografiya", count=2))

    assert mock_client.aio.models.generate_content.call_count == 1


@pytest.mark.django_db(transaction=True)
def test_generate_questions_with_material_passes_material_in_prompt(gemini_settings):
    mock_client = _make_mock_gemini_client(_SAMPLE_QUESTIONS)
    material = "Bu O'zbekiston tarixi haqida matn. Toshkent poytaxt."

    with patch("services.ai_generator_service.genai.Client", return_value=mock_client):
        result = asyncio.run(generate_questions(topic="Tarix", count=2, material=material))

    assert len(result) == 2
    call_args = mock_client.aio.models.generate_content.call_args
    prompt = call_args.kwargs.get("contents") or call_args.args[1]
    assert material in prompt


@pytest.mark.django_db(transaction=True)
def test_generate_questions_skips_invalid_correct_option(gemini_settings):
    bad_questions = [{
        "question": "Savol?",
        "option_a": "A", "option_b": "B", "option_c": "C", "option_d": "D",
        "correct_option": "E", "explanation": "",
    }]
    mock_client = _make_mock_gemini_client(bad_questions)

    with patch("services.ai_generator_service.genai.Client", return_value=mock_client):
        result = asyncio.run(generate_questions(topic="Test", count=1))

    assert result == []


@pytest.mark.django_db(transaction=True)
def test_generate_questions_skips_empty_question(gemini_settings):
    bad_questions = [{
        "question": "",
        "option_a": "A", "option_b": "B", "option_c": "C", "option_d": "D",
        "correct_option": "A", "explanation": "",
    }]
    mock_client = _make_mock_gemini_client(bad_questions)

    with patch("services.ai_generator_service.genai.Client", return_value=mock_client):
        result = asyncio.run(generate_questions(topic="Test", count=1))

    assert result == []


@pytest.mark.django_db(transaction=True)
def test_generate_questions_truncates_long_fields(gemini_settings):
    long_questions = [{
        "question": "x" * 300,
        "option_a": "y" * 150, "option_b": "B", "option_c": "C", "option_d": "D",
        "correct_option": "A",
        "explanation": "z" * 250,
    }]
    mock_client = _make_mock_gemini_client(long_questions)

    with patch("services.ai_generator_service.genai.Client", return_value=mock_client):
        result = asyncio.run(generate_questions(topic="Test", count=1))

    assert len(result) == 1
    assert len(result[0]["question_text"]) == 250
    assert len(result[0]["option_a"]) == 100
    assert len(result[0]["explanation"]) == 200


@pytest.mark.django_db(transaction=True)
def test_generate_questions_returns_empty_on_empty_text(gemini_settings):
    mock_response = MagicMock()
    mock_response.text = ""
    mock_client = MagicMock()
    mock_client.aio = MagicMock()
    mock_client.aio.models = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    with patch("services.ai_generator_service.genai.Client", return_value=mock_client):
        result = asyncio.run(generate_questions(topic="Test", count=5))

    assert result == []


@pytest.mark.django_db(transaction=True)
def test_generate_questions_returns_empty_on_invalid_json(gemini_settings):
    mock_response = MagicMock()
    mock_response.text = "[not valid json"
    mock_client = MagicMock()
    mock_client.aio = MagicMock()
    mock_client.aio.models = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    with patch("services.ai_generator_service.genai.Client", return_value=mock_client):
        result = asyncio.run(generate_questions(topic="Test", count=5))

    assert result == []


@pytest.mark.django_db(transaction=True)
def test_generate_questions_returns_empty_when_no_api_key(db):
    s = AiProviderSettings.load()
    s.active_provider = AiProviderSettings.Provider.GEMINI
    s.gemini_api_key = ""
    s.save()

    result = asyncio.run(generate_questions(topic="Test", count=5))
    assert result == []


# --- generate_questions_detailed / failure logging ---

@pytest.mark.django_db(transaction=True)
def test_generate_questions_detailed_success_reports_model(gemini_settings):
    mock_client = _make_mock_gemini_client(_SAMPLE_QUESTIONS)

    with patch("services.ai_generator_service.genai.Client", return_value=mock_client):
        result = asyncio.run(generate_questions_detailed(topic="Geografiya", count=2))

    assert len(result.questions) == 2
    assert result.error_message == ""
    assert result.model_used == "gemini/gemini-2.0-flash"


@pytest.mark.django_db(transaction=True)
def test_generate_questions_detailed_returns_reason_instead_of_raising(gemini_settings):
    mock_client = _make_mock_gemini_client(_SAMPLE_QUESTIONS)
    denied = genai_errors.ClientError(401, {"error": {"code": 401, "message": "bad key", "status": "UNAUTHENTICATED"}})
    mock_client.aio.models.generate_content = AsyncMock(side_effect=denied)

    with patch("services.ai_generator_service.genai.Client", return_value=mock_client):
        result = asyncio.run(generate_questions_detailed(topic="Geografiya", count=2))

    assert result.questions == []
    assert "401" in result.error_message
    assert "ClientError" in result.error_details


@pytest.mark.django_db(transaction=True)
def test_generate_questions_detailed_lists_tried_models_when_all_busy(gemini_settings):
    mock_client = _make_mock_gemini_client(_SAMPLE_QUESTIONS)
    busy = genai_errors.ServerError(503, {"error": {"code": 503, "message": "busy", "status": "UNAVAILABLE"}})
    mock_client.aio.models.generate_content = AsyncMock(side_effect=busy)

    with patch("services.ai_generator_service.genai.Client", return_value=mock_client):
        result = asyncio.run(generate_questions_detailed(topic="Geografiya", count=2))

    assert "503" in result.error_message
    assert "gemini-flash-lite-latest" in result.error_details


@pytest.mark.django_db(transaction=True)
def test_generate_questions_detailed_reports_missing_api_key(db):
    s = AiProviderSettings.load()
    s.active_provider = AiProviderSettings.Provider.GEMINI
    s.gemini_api_key = ""
    s.save()

    result = asyncio.run(generate_questions_detailed(topic="Test", count=5))
    assert result.questions == []
    assert "API kaliti" in result.error_message


@pytest.mark.django_db(transaction=True)
def test_generate_questions_detailed_reports_invalid_json(gemini_settings):
    mock_response = MagicMock()
    mock_response.text = "[not valid json"
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    with patch("services.ai_generator_service.genai.Client", return_value=mock_client):
        result = asyncio.run(generate_questions_detailed(topic="Test", count=5))

    assert result.questions == []
    assert "JSON" in result.error_message
    assert "[not valid json" in result.error_details


@pytest.mark.django_db(transaction=True)
def test_create_ai_log_marks_failure(user, gemini_settings):
    log = asyncio.run(create_ai_log(
        user_id=user.id, topic="slides", questions_count=0, requested_count=10,
        source_filename="slides.pptx", model_used="gemini/gemini-flash-latest",
        error_message="Provayder serveri band (503)", error_details="Traceback ...", duration_ms=1200,
    ))

    assert log.status == AiGenerationLog.Status.FAILED
    assert log.source_filename == "slides.pptx"
    assert log.model_used == "gemini/gemini-flash-latest"
    assert log.error_message.startswith("Provayder")


@pytest.mark.django_db(transaction=True)
def test_create_ai_log_defaults_to_success(user, gemini_settings):
    log = asyncio.run(create_ai_log(user_id=user.id, topic="Tarix", questions_count=5))
    assert log.status == AiGenerationLog.Status.SUCCESS
    assert log.error_message == ""
