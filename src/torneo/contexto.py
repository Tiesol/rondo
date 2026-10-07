"""Procesadores de contexto: lo que todas las plantillas necesitan."""

from django.http import HttpRequest

from torneo.models import Organizador
from torneo.permisos import MESA, nombre_del_rol


def organizador(request: HttpRequest) -> dict[str, Organizador]:
    return {"organizador": Organizador.actual()}


def rol(request: HttpRequest) -> dict[str, str]:
    """El rol de quien mira, para la barra superior ("Organización" o "Mesa")."""
    nombre = nombre_del_rol(request.user)
    return {"rol": nombre, "rol_corto": "Mesa" if nombre == MESA else nombre}
