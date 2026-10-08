"""Encabezados de seguridad que Django no pone solo (T6.3)."""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

# La app no usa cámara, micrófono, ubicación ni pagos: se apagan para todo el sitio.
PERMISOS = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"


class PermisosDelNavegador:
    def __init__(self, siguiente: Callable[[HttpRequest], HttpResponse]) -> None:
        self.siguiente = siguiente

    def __call__(self, request: HttpRequest) -> HttpResponse:
        respuesta = self.siguiente(request)
        respuesta.setdefault("Permissions-Policy", PERMISOS)
        return respuesta
