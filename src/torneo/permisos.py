"""Roles y control de acceso a las vistas (docs/DISENO.md, "Roles").

Organización puede todo. Mesa de control carga equipos y listas, verifica jugadores y ve el
calendario. Ver es para cualquiera con sesión; lo demás pide uno de los permisos de Torneo.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

ORGANIZACION = "Organización"
MESA = "Mesa de control"

# Permisos propios (Torneo.Meta.permissions) de cada rol. La migración 0004 crea los grupos.
PERMISOS_POR_ROL: dict[str, list[str]] = {
    ORGANIZACION: [
        "configurar_torneo",
        "programar_partidos",
        "inscribir_equipos",
        "verificar_jugadores",
    ],
    MESA: ["inscribir_equipos", "verificar_jugadores"],
}

Vista = Callable[..., HttpResponse]


def nombre_del_rol(usuario: AbstractBaseUser | AnonymousUser) -> str:
    """El rol que se muestra; vacío si no tiene ninguno."""
    if not usuario.is_authenticated:
        return ""
    if getattr(usuario, "is_superuser", False):
        return ORGANIZACION
    grupos = set(usuario.groups.values_list("name", flat=True))  # type: ignore[attr-defined]
    for rol in (ORGANIZACION, MESA):
        if rol in grupos:
            return rol
    return ""


def requiere(permiso: str, que: str) -> Callable[[Vista], Vista]:
    """Sin el permiso, la vista dice "Solo la organización puede <que>" con un 403."""

    def decorador(vista: Vista) -> Vista:
        @wraps(vista)
        def envuelta(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            if not request.user.has_perm(permiso):
                return render(request, "sin_permiso.html", {"que": que}, status=403)
            return vista(request, *args, **kwargs)

        return envuelta

    return decorador
