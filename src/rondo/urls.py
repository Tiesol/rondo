from django.contrib import admin
from django.urls import include, path

from torneo.views import inicio

urlpatterns = [
    path("", inicio, name="inicio"),
    path("cuentas/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
]
