from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("users/", include("apps.users.urls")),
    path("quizzes/", include("apps.quizzes.urls")),
    path("moderation/", include("apps.moderation.urls")),
]
