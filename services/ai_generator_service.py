import json
import logging
import traceback
from dataclasses import dataclass, field

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


@dataclass
class GenerationResult:
    questions: list[dict] = field(default_factory=list)
    model_used: str = ""
    error_message: str = ""
    error_details: str = ""


def _parse_questions(text: str, topic: str) -> tuple[list[dict], str]:
    """Savollar ro'yxati va (bo'sh bo'lsa) sababini qaytaradi."""
    start = text.find("[")
    end = text.rfind("]") + 1
    if start == -1 or end == 0:
        logger.error("generate_questions: JSON topilmadi, topic=%s, response=%s", topic, text[:300])
        return [], "AI javobida JSON massiv topilmadi (javob kesilgan yoki formatga mos emas)."

    try:
        raw_list = json.loads(text[start:end])
    except json.JSONDecodeError:
        logger.exception("generate_questions: JSON parse xato, topic=%s", topic)
        return [], "AI javobidagi JSON buzilgan (ko'pincha javob uzunlik limitida kesilganda)."

    if not isinstance(raw_list, list):
        logger.error("generate_questions: JSON massiv emas, topic=%s", topic)
        return [], "AI javobi JSON massiv emas."

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

    if not valid:
        return [], f"AI {len(raw_list)} ta element qaytardi, lekin birortasi ham to'liq/to'g'ri savol emas."
    return valid, ""


_GEMINI_FALLBACK_MODELS = ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-2.5-flash"]
_GEMINI_RETRYABLE_CODES = {404, 429, 503}

_STATUS_REASONS = {
    400: "So'rov rad etildi (400): matn juda uzun, model bu so'rovni qo'llamaydi yoki parametr noto'g'ri.",
    401: "API kalit noto'g'ri yoki muddati o'tgan (401). Admin paneldagi kalitni tekshiring.",
    403: "API kalitga bu modeldan foydalanishga ruxsat yo'q yoki hudud cheklovi (403).",
    404: "Model topilmadi (404): model nomi eskirgan yoki noto'g'ri.",
    408: "Provayder javob berishga ulgurmadi (408).",
    413: "Yuborilgan matn juda katta (413).",
    429: "So'rovlar limiti yoki kvota tugadi (429). Biroz kuting yoki tarifni tekshiring.",
    500: "Provayder serverida ichki xato (500).",
    502: "Provayder shlyuzida xato (502).",
    503: "Provayder serveri band (503) — zaxira modellar ham javob bermadi.",
    504: "Provayder javob berishga ulgurmadi (504).",
    529: "Provayder haddan tashqari yuklangan (529).",
}


@dataclass
class _ProviderReply:
    text: str
    model: str
    empty_reason: str = ""


def describe_ai_error(exc: BaseException) -> str:
    """Exception'ni admin uchun tushunarli o'zbekcha sababga aylantiradi."""
    code = None
    if isinstance(exc, genai_errors.APIError):
        code = exc.code
    elif isinstance(exc, (anthropic.APIStatusError, openai.APIStatusError)):
        code = exc.status_code
    elif isinstance(exc, (anthropic.APITimeoutError, openai.APITimeoutError, TimeoutError)):
        return "Provayder javob berishga ulgurmadi (timeout)."
    elif isinstance(exc, (anthropic.APIConnectionError, openai.APIConnectionError, ConnectionError)):
        return "Provayder serveriga ulanib bo'lmadi (tarmoq xatosi)."

    if code is not None:
        return _STATUS_REASONS.get(code, f"Provayder {code} xato kodini qaytardi.")
    return f"Kutilmagan xato: {type(exc).__name__}: {str(exc)[:300]}"


async def _generate_gemini(prompt: str, model: str, api_key: str) -> _ProviderReply:
    client = genai.Client(api_key=api_key)
    models = [model] + [m for m in _GEMINI_FALLBACK_MODELS if m != model]
    last_error: genai_errors.APIError | None = None
    attempts: list[str] = []

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
            attempts.append(f"{candidate} → {exc.code}")
            last_error = exc
            continue

        text = response.text or ""
        empty_reason = ""
        if not text:
            first = (response.candidates or [None])[0]
            empty_reason = f"Gemini bo'sh javob qaytardi (finish_reason={getattr(first, 'finish_reason', None)})."
        return _ProviderReply(text=text, model=f"gemini/{candidate}", empty_reason=empty_reason)

    last_error.add_note("Sinab ko'rilgan modellar: " + ", ".join(attempts))
    raise last_error


async def _generate_claude(prompt: str, model: str, api_key: str) -> _ProviderReply:
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
            return _ProviderReply(text=block.text, model=f"claude/{model}")
    return _ProviderReply(
        text="", model=f"claude/{model}",
        empty_reason=f"Claude matn qaytarmadi (stop_reason={message.stop_reason}).",
    )


async def _generate_openai(prompt: str, model: str, api_key: str) -> _ProviderReply:
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
    choice = response.choices[0]
    text = choice.message.content or ""
    empty_reason = "" if text else f"OpenAI bo'sh javob qaytardi (finish_reason={choice.finish_reason})."
    return _ProviderReply(text=text, model=f"openai/{model}", empty_reason=empty_reason)


async def _generate(topic: str, count: int, material: str | None) -> GenerationResult:
    """API xatolarini yuqoriga ko'taradi; boshqa muvaffaqiyatsizliklar sababini natijada qaytaradi."""
    ai_settings = await _load_ai_settings()
    provider = ai_settings.active_provider

    if material:
        prompt = _MATERIAL_PROMPT_TEMPLATE.format(count=count, material=material[:_MAX_MATERIAL_CHARS])
    else:
        prompt = _TOPIC_PROMPT_TEMPLATE.format(count=count, topic=topic)

    providers = {
        AiProviderSettings.Provider.GEMINI: (_generate_gemini, ai_settings.gemini_api_key, ai_settings.gemini_model),
        AiProviderSettings.Provider.CLAUDE: (_generate_claude, ai_settings.claude_api_key, ai_settings.claude_model),
        AiProviderSettings.Provider.OPENAI: (_generate_openai, ai_settings.openai_api_key, ai_settings.openai_model),
    }
    if provider not in providers:
        return GenerationResult(error_message=f"Noma'lum AI provayder: {provider}")

    generate, api_key, model = providers[provider]
    if not api_key:
        logger.error("generate_questions: %s API kaliti yo'q", provider)
        return GenerationResult(
            model_used=f"{provider}/{model}",
            error_message=f"{ai_settings.get_active_provider_display()} API kaliti admin panelda kiritilmagan.",
        )

    reply = await generate(prompt, model, api_key)
    if not reply.text:
        logger.error("generate_questions: API bo'sh javob qaytardi, topic=%s", topic)
        return GenerationResult(model_used=reply.model, error_message=reply.empty_reason or "AI bo'sh javob qaytardi.")

    questions, reason = _parse_questions(reply.text, topic)
    return GenerationResult(
        questions=questions,
        model_used=reply.model,
        error_message=reason,
        error_details="" if questions else f"AI javobining boshi:\n{reply.text[:1500]}",
    )


async def generate_questions(
    topic: str,
    count: int,
    material: str | None = None,
) -> list[dict]:
    result = await _generate(topic, count, material)
    return result.questions


async def generate_questions_detailed(
    topic: str,
    count: int,
    material: str | None = None,
) -> GenerationResult:
    """Exception ko'tarmaydi — xato sababi natija ichida qaytadi (admin logi uchun)."""
    try:
        return await _generate(topic, count, material)
    except Exception as exc:  # provayder SDK'lari turli xil xato turlarini ko'taradi
        logger.exception("generate_questions_detailed xato: topic=%s", topic)
        return GenerationResult(
            error_message=describe_ai_error(exc),
            error_details="".join(traceback.format_exception(exc))[-6000:],
        )


@sync_to_async
def create_ai_log(
    user_id: int,
    topic: str,
    questions_count: int,
    *,
    requested_count: int = 0,
    model_used: str = "",
    source_filename: str = "",
    error_message: str = "",
    error_details: str = "",
    duration_ms: int = 0,
) -> AiGenerationLog | None:
    try:
        if not model_used:
            ai_settings = AiProviderSettings.load()
            model_label = {
                "gemini": ai_settings.gemini_model,
                "claude": ai_settings.claude_model,
                "openai": ai_settings.openai_model,
            }.get(ai_settings.active_provider, "unknown")
            model_used = f"{ai_settings.active_provider}/{model_label}"
        return AiGenerationLog.objects.create(
            user_id=user_id,
            topic=topic[:255],
            source_filename=source_filename[:255],
            requested_count=requested_count,
            questions_count=questions_count,
            model_used=model_used[:100],
            status=AiGenerationLog.Status.FAILED if error_message else AiGenerationLog.Status.SUCCESS,
            error_message=error_message,
            error_details=error_details,
            duration_ms=duration_ms,
        )
    except DatabaseError:
        logger.exception("create_ai_log xato: user_id=%s, topic=%s", user_id, topic)
        return None
