---
name: decision
description: decisions/ papkasiga arxitektura qarori yozish
---

# /decision buyrug'i

## Nima qiladi
`D:/ObsidianVault/QuizBot/decisions/YYYY-MM-DD-<slug>.md` faylini yaratadi.

## Fayl formati
```markdown
---
sana: YYYY-MM-DD
teglar: [qaror, <mavzu>]
---
# Qaror: <sarlavha>

## Muammo
<Nima muammo bor edi? Nima tanlov oldida turdik?>

## Tanlovlar
1. **<Variant A>** — <afzalliklari / kamchiliklari>
2. **<Variant B>** — <afzalliklari / kamchiliklari>

## Qaror
<Qaysi variant tanlandi va nima uchun>

## Oqibatlar
<Bu qarorning keyingi ishlarga ta'siri>
```

## Qachon chaqiriladi
- Yangi servis arxitekturasi tanlanganda
- Muhim stack o'zgarishi (kutubxona almashtirish va h.k.)
- DB sxema dizayni muhokama qilinganda
- Performance/xavfsizlik trade-off qilinganda
