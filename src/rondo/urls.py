from django.contrib import admin
from django.urls import include, path

from torneo.views import diagnostico, inicio, mas, reglas

urlpatterns = [
    path("", inicio, name="inicio"),
    path("mas/", mas, name="mas"),
    path("torneos/<int:pk>/reglas/", reglas, name="reglas"),
    path("cuentas/", include("django.contrib.auth.urls")),
    path("diagnostico/png/", diagnostico.png, name="diagnostico-png"),
    path("diagnostico/componentes/", diagnostico.componentes, name="diagnostico-componentes"),
    path("admin/", admin.site.urls),
]
