"""Programar (T3.7): por ahora, "¿Entra todo?". El programador llega en la fase 4."""

from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from dominio.capacidad import GrupoDeCanchas
from torneo.models import Torneo
from torneo.permisos import requiere
from torneo.servicios.capacidad import capacidad_del_torneo


def _horas(minutos: int) -> str:
    horas = minutos / 60
    return (
        f"{horas:.0f}" if horas >= 10 or horas == int(horas) else f"{horas:.1f}".replace(".", ",")
    )


def _fila(grupo: GrupoDeCanchas, escenario: str) -> dict[str, Any]:
    canchas = " y ".join(grupo.canchas) or "Sin canchas compatibles"
    return {
        "titulo": f"{canchas} · {escenario}",
        "categorias": ", ".join(grupo.categorias),
        "pedido": _horas(grupo.pedido),
        "disponible": _horas(grupo.disponible),
        "faltan": _horas(grupo.faltan),
        "entra": grupo.entra,
        "uso": min(round(100 * grupo.pedido / grupo.disponible), 100) if grupo.disponible else 100,
    }


@requiere("torneo.configurar_torneo", "programar")
def programar(request: HttpRequest, pk: int) -> HttpResponse:
    torneo = get_object_or_404(Torneo, pk=pk)
    capacidad = capacidad_del_torneo(torneo)
    desde = capacidad.eliminacion_desde
    filas = [_fila(g, "todo el torneo") for g in capacidad.total] + [
        _fila(g, f"eliminación, desde el fin de semana {desde}") for g in capacidad.eliminacion
    ]
    return render(
        request,
        "torneo/programar.html",
        {
            "torneo": torneo,
            "filas": filas,
            "capacidad": capacidad,
            "estimadas": ", ".join(capacidad.estimadas),
            "sin_formato": ", ".join(capacidad.sin_formato),
        },
    )
