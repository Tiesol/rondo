from django.contrib import admin
from django.urls import include, path

from torneo.views import asistente, diagnostico, inicio, mas, reglas

urlpatterns = [
    path("", inicio, name="inicio"),
    path("mas/", mas, name="mas"),
    path("torneos/nuevo/", asistente.empezar, name="crear-torneo"),
    path("torneos/nuevo/<int:paso>/", asistente.asistente, name="asistente"),
    path("torneos/<int:pk>/reglas/", reglas, name="reglas"),
    path("cuentas/", include("django.contrib.auth.urls")),
    path("diagnostico/png/", diagnostico.png, name="diagnostico-png"),
    path("diagnostico/componentes/", diagnostico.componentes, name="diagnostico-componentes"),
    path("admin/", admin.site.urls),
]
