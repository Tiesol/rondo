"""Lo que necesita atención en el torneo, para la lista de Inicio (TU.5).

Sin barra de avance: solo pendientes concretos, cada uno con un enlace a donde se resuelve.
Categorías sin equipos, equipos debajo del mínimo y reglas sin confirmar.
"""

from collections.abc import Iterable
from typing import Any

from django.db.models import Count
from django.urls import reverse

from dominio.config import describir_reglas
from torneo.models import Equipo, Torneo


def pendientes(torneo: Torneo, *, puede_configurar: bool) -> list[dict[str, Any]]:
    lista: list[dict[str, Any]] = []

    categorias = torneo.categorias.annotate(cantidad=Count("equipos"))
    sin_equipos = [c for c in categorias if c.cantidad == 0]
    if sin_equipos:
        lista.append(
            {
                "titulo": _contar(
                    len(sin_equipos), "categoría sin equipos", "categorías sin equipos"
                ),
                "sub": _primeros(str(c) for c in sin_equipos),
                "url": reverse("categoria", args=[sin_equipos[0].pk, "equipos"]),
                "icono": "torneo",
                "estado": "aviso",
            }
        )

    cortos = [
        e
        for e in Equipo.objects.filter(categoria__torneo=torneo)
        .select_related("categoria")
        .annotate(cantidad=Count("jugadores"))
        if e.cantidad < e.categoria.min_jugadores
    ]
    if cortos:
        lista.append(
            {
                "titulo": _contar(
                    len(cortos),
                    "equipo debajo del mínimo de jugadores",
                    "equipos debajo del mínimo de jugadores",
                ),
                "sub": _primeros(f"{e.nombre} ({e.categoria})" for e in cortos),
                "url": reverse("equipo", args=[cortos[0].pk, "plantel"]),
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


def _contar(cantidad: int, singular: str, plural: str) -> str:
    return f"{cantidad} {singular if cantidad == 1 else plural}"


def _primeros(nombres: Iterable[str], cuantos: int = 3) -> str:
    """ "A, B y C", o "A, B, C y 4 más"."""
    lista = list(nombres)
    if len(lista) > cuantos:
        return f"{', '.join(lista[:cuantos])} y {len(lista) - cuantos} más"
    return lista[0] if len(lista) == 1 else f"{', '.join(lista[:-1])} y {lista[-1]}"
