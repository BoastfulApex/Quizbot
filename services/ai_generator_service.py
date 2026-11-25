import json
import logging

import anthropic
import openai
from asgiref.sync import sync_to_async
from django.db import DatabaseError
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from apps.moderation.models import AiGenerationLog, AiProviderSettings
from bot.utils.limits import MAX_EXPLANATION_LEN, MAX_OPTION_LEN, MAX_QUESTION_LEN

logger = logging.getLogger(__name__)

_VALID_OPTIONS = {"A", "B", "C", "D"}
_MAX_MATERIAL_CHARS = 12_000

_SYSTEM_PROMPT = (
    "Sen test savollari yaratuvchi yordamchisan. "
    "O'zbek tilida test savollari yaratasan. "
    "Faqat so'ralgan JSON formatida javob berasan — boshqa hech qanday matn yozma."
)

_TOPIC_PROMPT_TEMPLATE = """Quyidagi mavzu bo'yicha {count} ta test savoli yarat: {topic}

Faqat quyidagi JSON massiv formatida qaytarib ber (boshqa hech narsa yozma):
[
  {{
    "question": "Savol matni (maksimal 250 belgi)",
    "option_a": "A varianti (maksimal 100 belgi)",
    "option_b": "B varianti (maksimal 100 belgi)",
    "option_c": "C varianti (maksimal 100 belgi)",
    "option_d": "D varianti (maksimal 100 belgi)",
    "correct_option": "A",
    "explanation": "Izoh (maksimal 200 belgi, ixtiyoriy)"
  }}
]

Qoidalar:
- Faqat JSON massiv qaytargin
- correct_option faqat "A", "B", "C" yoki "D" bo'lsin
- Savollar turli xil va to'g'ri bo'lsin
- O'zbek tilida yoz
"""

_MATERIAL_PROMPT_TEMPLATE = """Quyidagi matn asosida {count} ta test savoli yarat:

--- MATN BOSHI ---
{material}
--- MATN OXIRI ---

Faqat quyidagi JSON massiv formatida qaytarib ber (boshqa hech narsa yozma):
[
  {{
    "question": "Savol matni (maksimal 250 belgi)",
    "option_a": "A varianti (maksimal 100 belgi)",
    "option_b": "B varianti (maksimal 100 belgi)",
    "option_c": "C varianti (maksimal 100 belgi)",
    "option_d": "D varianti (maksimal 100 belgi)",
    "correct_option": "A",
    "explanation": "Izoh (maksimal 200 belgi, ixtiyoriy)"
  }}
]

Qoidalar:
- Faqat yuqoridagi matn mazmuniga asoslanib savol tuz
- Faqat JSON massiv qaytargin
- correct_option faqat "A", "B", "C" yoki "D" bo'lsin
- O'zbek tilida yoz
"""


@sync_to_async
def _load_ai_settings() -> AiProviderSettings:
    return AiProviderSettings.load()


def _parse_questions(text: str, topic: str) -> list[dict]:
    start = text.find("[")
    end = text.rfind("]") + 1
    if start == -1 or end == 0:
        logger.error("generate_questions: JSON topilmadi, topic=%s, response=%s", topic, text[:300])
        return []

    try:
        raw_list = json.loads(text[start:end])
    except json.JSONDecodeError:
        logger.exception("generate_questions: JSON parse xato, topic=%s", topic)
        return []

    if not isinstance(raw_list, list):
        logger.error("generate_questions: JSON massiv emas, topic=%s", topic)
        return []

    valid: list[dict] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        question_text = str(item.get("question", "")).strip()
        option_a = str(item.get("option_a", "")).strip()
        option_b = str(item.get("option_b", "")).strip()
        option_c = str(item.get("option_c", "")).strip()
        option_d = str(item.get("option_d", "")).strip()
        correct = str(item.get("correct_option", "")).strip().upper()
        explanation = str(item.get("explanation", "")).strip()

        if not question_text or not option_a or not option_b or not option_c or not option_d:
            continue
        if correct not in _VALID_OPTIONS:
            continue

        valid.append({
            "question_text": question_text[:MAX_QUESTION_LEN],
            "option_a": option_a[:MAX_OPTION_LEN],
            "option_b": option_b[:MAX_OPTION_LEN],
            "option_c": option_c[:MAX_OPTION_LEN],
            "option_d": option_d[:MAX_OPTION_LEN],
            "correct_option": correct,
            "explanation": explanation[:MAX_EXPLANATION_LEN],
            "difficulty": "",
        })

    return valid


_GEMINI_FALLBACK_MODELS = ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-2.5-flash"]
_GEMINI_RETRYABLE_CODES = {404, 429, 503}


async def _generate_gemini(prompt: str, model: str, api_key: str) -> str:
    client = genai.Client(api_key=api_key)
    models = [model] + [m for m in _GEMINI_FALLBACK_MODELS if m != model]
    last_error: genai_errors.APIError | None = None

    for candidate in models:
        try:
            response = await client.aio.models.generate_content(
                model=candidate,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    temperature=0.7,
                    max_output_tokens=8000,
                ),
            )
        except genai_errors.APIError as exc:
            if exc.code not in _GEMINI_RETRYABLE_CODES:
                raise
            logger.warning("_generate_gemini: %s modeli %s qaytardi, keyingisi sinaladi", candidate, exc.code)
            last_error = exc
            continue
        return response.text or ""

    raise last_error


async def _generate_claude(prompt: str, model: str, api_key: str) -> str:
    client = anthropic.AsyncAnthropic(api_key=api_key)
    async with client.messages.stream(
        model=model,
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        message = await stream.get_final_message()
    for block in message.content:
        if block.type == "text":
            return block.text
    return ""


async def _generate_openai(prompt: str, model: str, api_key: str) -> str:
    client = openai.AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=8000,
        temperature=0.7,
    )
    return response.choices[0].message.content or ""


async def generate_questions(
    topic: str,
    count: int,
    material: str | None = None,
) -> list[dict]:
    ai_settings = await _load_ai_settings()
    provider = ai_settings.active_provider

    if material:
        prompt = _MATERIAL_PROMPT_TEMPLATE.format(
            count=count,
            material=material[:_MAX_MATERIAL_CHARS],
        )
    else:
        prompt = _TOPIC_PROMPT_TEMPLATE.format(count=count, topic=topic)

    text = ""
    if provider == AiProviderSettings.Provider.GEMINI:
        if not ai_settings.gemini_api_key:
            logger.error("generate_questions: Gemini API kaliti yo'q")
            return []
        text = await _generate_gemini(prompt, ai_settings.gemini_model, ai_settings.gemini_api_key)
    elif provider == AiProviderSettings.Provider.CLAUDE:
        if not ai_settings.claude_api_key:
            logger.error("generate_questions: Claude API kaliti yo'q")
            return []
        text = await _generate_claude(prompt, ai_settings.claude_model, ai_settings.claude_api_key)
    elif provider == AiProviderSettings.Provider.OPENAI:
        if not ai_settings.openai_api_key:
            logger.error("generate_questions: OpenAI API kaliti yo'q")
            return []
        text = await _generate_openai(prompt, ai_settings.openai_model, ai_settings.openai_api_key)

    if not text:
        logger.error("generate_questions: API bo'sh javob qaytardi, topic=%s", topic)
        return []

    return _parse_questions(text, topic)


@sync_to_async
def create_ai_log(
    user_id: int,
    topic: str,
    questions_count: int,
) -> AiGenerationLog | None:
    try:
        ai_settings = AiProviderSettings.load()
        model_label = {
            "gemini": ai_settings.gemini_model,
            "claude": ai_settings.claude_model,
            "openai": ai_settings.openai_model,
        }.get(ai_settings.active_provider, "unknown")
        return AiGenerationLog.objects.create(
            user_id=user_id,
            topic=topic,
            questions_count=questions_count,
            model_used=f"{ai_settings.active_provider}/{model_label}",
        )
    except DatabaseError:
        logger.exception("create_ai_log xato: user_id=%s, topic=%s", user_id, topic)
        return None
