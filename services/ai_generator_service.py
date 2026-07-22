import json
import logging

import anthropic
from asgiref.sync import sync_to_async
from django.db import DatabaseError

from apps.moderation.models import AiGenerationLog
from bot.utils.limits import MAX_EXPLANATION_LEN, MAX_OPTION_LEN, MAX_QUESTION_LEN
from data.config import settings

logger = logging.getLogger(__name__)

_MODEL = "claude-opus-4-8"
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


async def generate_questions(
    topic: str,
    count: int,
    model: str = _MODEL,
    material: str | None = None,
) -> list[dict]:
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    if material:
        prompt = _MATERIAL_PROMPT_TEMPLATE.format(
            count=count,
            material=material[:_MAX_MATERIAL_CHARS],
        )
    else:
        prompt = _TOPIC_PROMPT_TEMPLATE.format(count=count, topic=topic)

    async with client.messages.stream(
        model=model,
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        message = await stream.get_final_message()

    text = ""
    for block in message.content:
        if block.type == "text":
            text = block.text
            break

    if not text:
        logger.error("generate_questions: API bo'sh javob qaytardi, topic=%s", topic)
        return []

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


@sync_to_async
def create_ai_log(
    user_id: int,
    topic: str,
    questions_count: int,
    model: str = _MODEL,
) -> AiGenerationLog | None:
    try:
        return AiGenerationLog.objects.create(
            user_id=user_id,
            topic=topic,
            questions_count=questions_count,
            model_used=model,
        )
    except DatabaseError:
        logger.exception("create_ai_log xato: user_id=%s, topic=%s", user_id, topic)
        return None
