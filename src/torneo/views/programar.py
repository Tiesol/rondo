"""Programar (T3.7 y T4.6): "¿Entra todo?", el botón de programar y su resultado."""

from typing import Any

from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from dominio.capacidad import GrupoDeCanchas
from torneo.models import Corrida, Partido, Torneo
from torneo.permisos import requiere
from torneo.servicios.capacidad import capacidad_del_torneo
from torneo.servicios.programador import (
    ProgramacionEnCurso,
    Resumen,
    programar_torneo,
    resumen_antes_de_programar,
)
from torneo.views.confirmar import confirmado, pedir_confirmacion
from torneo.views.fragmentos import pide_fragmento


def _horas(minutos: int) -> str:
    horas = minutos / 60
    if horas >= 10 or horas == int(horas):
        return f"{horas:.0f}"
    return f"{horas:.1f}".replace(".", ",")


def _fila(grupo: GrupoDeCanchas, con_extra: GrupoDeCanchas | None = None) -> dict[str, Any]:
    return {
        "entra_con_extra": con_extra is not None and not grupo.entra and con_extra.entra,
        "titulo": " y ".join(grupo.canchas) or "Sin canchas compatibles",
        "categorias": ", ".join(grupo.categorias),
        "pedido": _horas(grupo.pedido),
        "disponible": _horas(grupo.disponible),
        "faltan": _horas(grupo.faltan),
        "entra": grupo.entra,
        "uso": min(round(100 * grupo.pedido / grupo.disponible), 100) if grupo.disponible else 100,
    }


def _plural(n: int, uno: str, varios: str) -> str:
    return f"{n} {uno if n == 1 else varios}"


def _que_pasa(resumen: Resumen) -> str:
    mueve = _plural(resumen.futuros, "partido ya programado", "partidos ya programados")
    return f"Volver a programar mueve {mueve} y ubica los que faltan. Nada se ubica antes de ahora."


def _detalle(resumen: Resumen) -> list[str]:
    lineas = []
    if resumen.jugados:
        jugados = _plural(resumen.jugados, "jugado o en juego", "jugados o en juego")
        lineas.append(f"No se mueven: {jugados}.")
    if resumen.sin_resultado:
        pasados = _plural(
            len(resumen.sin_resultado), "partido cuya hora ya pasó", "partidos cuya hora ya pasó"
        )
        lineas.append(f"No se mueven: {pasados}, y les falta el resultado.")
    lineas.append(f"Se mueven: {_plural(resumen.futuros, 'partido', 'partidos')} programados.")
    return lineas


def _resultado(torneo: Torneo) -> dict[str, Any] | None:
    """La última programación terminada, lista para mostrar."""
    corrida = (
        Corrida.objects.filter(torneo=torneo, tipo=Corrida.Tipo.PROGRAMAR)
        .exclude(estado=Corrida.Estado.CORRIENDO)
        .first()
    )
    if corrida is None:
        return None
    if corrida.estado == Corrida.Estado.FALLIDA:
        return {"fallida": True, "corrida": corrida}
    resultado = corrida.resultado
    # T11.2: los que se ubicaron a mano después ya no figuran.
    pendientes = set(
        Partido.objects.filter(
            categoria__torneo=torneo, estado=Partido.Estado.PENDIENTE
        ).values_list("pk", flat=True)
    )
    return {
        "corrida": corrida,
        "ubicados": resultado.get("ubicados", 0),
        "total": resultado.get("total", 0),
        "choques": sum(resultado.get("choques", {}).values()),
        "sin_ubicar": [s for s in resultado.get("sin_ubicar", []) if s["id"] in pendientes],
        "sin_resultado": resultado.get("sin_resultado", []),
    }


@requiere("torneo.configurar_torneo", "programar")
def programar(request: HttpRequest, pk: int) -> HttpResponse:
    torneo = get_object_or_404(Torneo, pk=pk)
    resumen = resumen_antes_de_programar(torneo)
    if request.method == "POST":
        faltan = request.POST.get("modo") == "faltan"
        if not faltan and resumen.hay_publicados and not confirmado(request):
            return pedir_confirmacion(
                request,
                mensaje=_que_pasa(resumen),
                detalle=_detalle(resumen),
                boton="Volver a programar",
                volver=reverse("programar", args=[torneo.pk]),
                peligro=True,
                destino="resultado-programacion",
            )
        try:
            programar_torneo(torneo, request.user, solo_lo_que_falta=faltan)
        except ProgramacionEnCurso as error:
            messages.error(request, str(error))
        if pide_fragmento(request):
            return render(
                request, "torneo/_resultado_programacion.html", {"resultado": _resultado(torneo)}
            )
        return redirect("programar", pk=torneo.pk)

    capacidad = capacidad_del_torneo(torneo)
    # T11.4: la eliminación ya no tiene un fin de semana propio; se mide todo el torneo.
    con_extra = {g.canchas: g for g in capacidad.con_extra}
    filas = [_fila(g, con_extra.get(g.canchas)) for g in capacidad.total]
    return render(
        request,
        "torneo/programar.html",
        {
            "torneo": torneo,
            "resumen": resumen,
            "filas": filas,
            "minutos_maximos": max(1, -(-settings.PROGRAMADOR_SEGUNDOS // 60)),
            "no_entra": any(not f["entra"] and not f["entra_con_extra"] for f in filas),
            "capacidad": capacidad,
            "estimadas": ", ".join(capacidad.estimadas),
            "sin_formato": ", ".join(capacidad.sin_formato),
            "resultado": _resultado(torneo),
        },
    )
