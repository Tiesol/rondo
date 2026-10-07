"""Lo que necesita atención en el torneo, para la lista de Inicio (TU.5).

Sin barra de avance: solo pendientes concretos, cada uno con un enlace a donde se resuelve.
Por ahora, lo que se sabe sin equipos; la fase 2 suma los de la inscripción.
"""

from typing import Any

from django.urls import reverse

from dominio.config import describir_reglas
from torneo.models import Torneo


def pendientes(torneo: Torneo, *, puede_configurar: bool) -> list[dict[str, Any]]:
    lista: list[dict[str, Any]] = []

    # Hasta la fase 2 no hay equipos: todas las categorías están vacías.
    sin_equipos = torneo.categorias.count()
    if sin_equipos:
        lista.append(
            {
                "titulo": f"{sin_equipos} categorías sin equipos",
                "sub": "La inscripción de equipos y listas llega en la próxima etapa",
                "url": reverse("torneo"),
                "icono": "personas",
                "estado": "aviso",
            }
        )

    if puede_configurar:
        con_pregunta = [d for d in describir_reglas() if d.pregunta]
        lista.append(
            {
                "titulo": f"{len(con_pregunta)} reglas esperan la respuesta del organizador",
                "sub": "Tienen un valor por defecto. Revísalas antes de programar",
                "url": reverse("reglas", args=[torneo.pk]),
                "icono": "documento",
                "estado": "info",
            }
        )
    return lista
