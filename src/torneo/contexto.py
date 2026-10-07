"""Procesadores de contexto: lo que todas las plantillas necesitan."""

from django.http import HttpRequest

from torneo.models import Organizador


def organizador(request: HttpRequest) -> dict[str, Organizador]:
    return {"organizador": Organizador.actual()}
