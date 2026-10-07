from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from torneo.views import (
    asistente,
    categoria,
    diagnostico,
    equipos,
    escuela,
    inicio,
    mas,
    reglas,
    torneo,
)
from torneo.views import publico as vistas_publicas
from torneo.views.publicar import publicar

urlpatterns = [
    path("", inicio, name="inicio"),
    path("mas/", mas, name="mas"),
    path("escuela/", escuela, name="escuela"),
    path("torneo/", torneo, name="torneo"),
    path("torneo/<int:pk>/equipos/nuevo/", equipos.nuevo_equipo, name="nuevo-equipo"),
    path("torneo/<int:pk>/<str:pestana>/", categoria, name="categoria"),
    path("equipos/<int:pk>/<str:seccion>/", equipos.equipo, name="equipo"),
    path("torneos/nuevo/", asistente.empezar, name="crear-torneo"),
    path("torneos/nuevo/<int:paso>/", asistente.asistente, name="asistente"),
    path("torneos/<int:pk>/reglas/", reglas, name="reglas"),
    path("torneos/<int:pk>/publico/", publicar, name="publicar"),
    path("t/<int:pk>/", vistas_publicas.publico, name="publico"),
    path(
        "t/<int:pk>/<int:categoria>/<str:pestana>/",
        vistas_publicas.categoria,
        name="publico-categoria",
    ),
    # Con la sesión iniciada, el login lleva al inicio en lugar de mostrarse vacío.
    path(
        "cuentas/login/",
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    path("cuentas/", include("django.contrib.auth.urls")),
    path("diagnostico/png/", diagnostico.png, name="diagnostico-png"),
    path("diagnostico/componentes/", diagnostico.componentes, name="diagnostico-componentes"),
    path("admin/", admin.site.urls),
]
