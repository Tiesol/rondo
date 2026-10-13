"""Procesadores de contexto: lo que todas las plantillas necesitan."""

from django.conf import settings
from django.http import HttpRequest

from torneo.models import Organizador
from torneo.permisos import MESA, nombre_del_rol
from torneo.presentacion import url_de_imagen


def organizador(request: HttpRequest) -> dict[str, object]:
    actual = Organizador.actual()
    return {"organizador": actual, "logo_url": url_de_imagen("logo", actual.pk, actual.logo.name)}


def rol(request: HttpRequest) -> dict[str, str]:
    """El rol de quien mira, para la barra superior ("Organización" o "Mesa")."""
    nombre = nombre_del_rol(request.user)
    return {"rol": nombre, "rol_corto": "Mesa" if nombre == MESA else nombre}


def imagenes(request: HttpRequest) -> dict[str, bool]:
    """Si se pueden subir imágenes: sin almacenamiento conectado, los campos avisan (T8.1)."""
    return {"imagenes_disponibles": settings.IMAGENES_DISPONIBLES}
