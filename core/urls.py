from django.urls import include, path

from data.config import settings

from apps.moderation.site import admin_site

# admin_site modellarni yuklash uchun import qilish kerak
import apps.quizzes.admin  # noqa: F401
import apps.users.admin  # noqa: F401

urlpatterns = [
    path(settings.ADMIN_URL, admin_site.urls),
    path("users/", include("apps.users.urls")),
    path("quizzes/", include("apps.quizzes.urls")),
    path("moderation/", include("apps.moderation.urls")),
]
