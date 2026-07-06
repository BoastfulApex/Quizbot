# Skill: Excel/CSV savol import qilish

## Kutilgan fayl formati
Ustunlar (aynan shu tartibda va nomda, sarlavha qatori bilan):
`savol | variant_a | variant_b | variant_c | variant_d | togri_javob | izoh | qiyinlik`

`togri_javob` qiymati faqat `A`, `B`, `C`, `D` bo'lishi mumkin (katta harf, boshqa
qiymatlar xato sifatida hisoblanadi).

## Validatsiya tartibi (services/import_service.py)
1. Fayl kengaytmasini tekshirish (`.xlsx`, `.csv` dan boshqasi rad etiladi)
2. `pandas.read_excel` / `pandas.read_csv` bilan o'qish, ustun nomlarini tekshirish
3. Har bir qator uchun: bo'sh maydonlarni, `togri_javob` qiymatini, dublikat savol
   matnini tekshirish
4. Xato qatorlar ro'yxati (`row_number`, `reason`) yig'iladi, muvaffaqiyatli qatorlar
   alohida yig'iladi
5. Faqat validatsiyadan o'tgan qatorlar bitta `bulk_create` chaqiruvi bilan bazaga
   yoziladi (har bir qator uchun alohida `.save()` chaqirilmaydi — tezlik uchun)
6. Natija admin/foydalanuvchiga: "✅ N ta qo'shildi / ❌ M ta xato" + xato tafsilotlari

## Muhim
- 1000+ qatorli fayllar uchun import jarayoni **asosiy event loop'ni bloklamasligi**
  kerak — `sync_to_async` yoki background task (`asyncio.create_task`) orqali bajariladi,
  foydalanuvchiga "⏳ Import boshlandi..." xabari darhol yuboriladi.
- `import_logs` jadvaliga har bir urinish yoziladi (kim, qachon, natija) — bu audit
  va limitlarni hisoblash uchun ham ishlatiladi (kunlik limit tekshiruvi shu jadvaldan).
