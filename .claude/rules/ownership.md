# Egalik (ownership) qoidalari

- Har bir `Quiz` obyektida `created_by` maydoni bor va u **hech qachon** null bo'lmasligi kerak.
- Test ustida yozish/o'chirish/share/unshare/schedule amali bajarilishidan oldin har doim:
  `request_user.id == quiz.created_by_id OR request_user.role in ("admin", "super_admin")`
  tekshiruvi bajarilishi shart.
- Bu tekshiruv handler ichida emas, balki `bot/middlewares/ownership_check.py` yoki
  `services/*_service.py` darajasida markazlashtirilgan bo'lishi kerak — har bir handlerda
  qayta yozilmasin.
- Guruhga share qilingan testni **faqat** `shared_by == current_user` yoki admin
  `/unshare` qila oladi (`group_shared_quizzes.shared_by` orqali tekshiriladi).
- Bloklangan (`is_blocked=True`) foydalanuvchining barcha `public` testlari va guruh
  share'lari avtomatik yashirilishi kerak — buni yangi query yozishda unutmang.
