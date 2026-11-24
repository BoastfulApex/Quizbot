---
name: ai-generate
description: Anthropic Claude API orqali savol generatsiyasi — streaming, adaptive thinking, JSON parse
triggers:
  - ai generatsiya
  - generate questions
  - anthropic
  - claude api
---
# Skill: AI savol generatsiyasi

## Asosiy pattern

```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic()

async with client.messages.stream(
    model="claude-opus-4-8",
    max_tokens=4096,
    thinking={"type": "adaptive"},
    messages=[{"role": "user", "content": prompt}],
) as stream:
    response = await stream.get_final_message()
```

## JSON parse qoidasi
- Claude javobidan faqat `[...]` yoki `{...}` qismini `re.search` bilan ajratib oling.
- Har bir savol validatsiyasi: `correct_option in {"A","B","C","D"}`, matn bo'sh emasligini tekshiring.
- Noto'g'ri savol o'tkazib yuboriladi (exception ko'tarilmaydi), log qilinadi.

## Maydon uzunliklari
| Maydon | Limit |
|---|---|
| `question` | 250 belgi |
| `option_a/b/c/d` | 100 belgi |
| `explanation` | 200 belgi |

## Material prompt (fayl yuklanganda)
- `_MAX_MATERIAL_CHARS = 12_000` — uzun matn qisqartiriladi.
- Fayl matnini prompt ichida `<material>...</material>` tegiga o'rang.

## Log yozish
`AiGenerationLog` modeliga `create_ai_log(user_id, topic, questions_count, model)` orqali yoziladi.
Muvaffaqiyatsiz generatsiyada ham log yoziladi (count=0).
