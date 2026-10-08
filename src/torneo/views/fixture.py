"""Fixture de una categoría: series, partidos por fecha y eliminación (T3.5).

Lo que se muestra no tiene datos de personas: sirve igual para la página pública.
"""

from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from dominio.formatos import FormatoFaltante
from torneo.models import CategoriaNivel, Equipo, Partido, Torneo
from torneo.permisos import requiere
from torneo.presentacion import escudo
from torneo.servicios.fixture import (
    FixtureNoSePuede,
    formatos,
    generar_fixture,
    generar_fixtures_faltantes,
    series_elegidas,
)

COPAS = {"oro": "Copa de Oro", "plata": "Copa de Plata", "bronce": "Bronce"}


def _lado(equipo: Equipo | None, texto: str) -> dict[str, Any]:
    if equipo is None:
        return {"nombre": texto, "escudo": None}
    return {"nombre": equipo.nombre, "escudo": escudo(equipo)}


def _fila(partido: Partido) -> dict[str, Any]:
    return {
        "local": _lado(partido.local, partido.texto_local),
        "visitante": _lado(partido.visitante, partido.texto_visitante),
        "nombre": partido.nombre,
        "serie": partido.serie.nombre if partido.serie else "",
    }


def datos_del_fixture(categoria: CategoriaNivel) -> dict[str, Any]:
    """Series, fechas y eliminación, listas para la plantilla torneo/_fixture.html."""
    cantidad = categoria.equipos.count()
    problema = ""
    letras: tuple[str, ...] = ()
    if cantidad >= 2:
        try:
            letras = formatos().para(cantidad).grupos.nombres_de_series
        except FormatoFaltante as error:
            problema = str(error)

    partidos = list(
        categoria.partidos.select_related("local", "visitante", "serie").order_by("fecha", "pk")
    )
    fechas: dict[int, list[dict[str, Any]]] = {}
    copas: dict[str, list[dict[str, Any]]] = {}
    for partido in partidos:
        if partido.fase == Partido.Fase.GRUPOS and partido.fecha:
            fechas.setdefault(partido.fecha, []).append(_fila(partido))
        else:
            copas.setdefault(COPAS.get(partido.copa, partido.copa), []).append(_fila(partido))
    return {
        "problema": problema,
        "faltan_equipos": cantidad < 2,
        "hay_fixture": bool(partidos),
        "letras": letras,
        "series": [
            {
                "nombre": serie.nombre,
                "modelos": modelos,  # para el editor de series
                "equipos": [e.nombre for e in modelos],
                "nombres": ", ".join(e.nombre for e in modelos),
            }
            for serie in categoria.series.prefetch_related("equipos")
            for modelos in [sorted(serie.equipos.all(), key=lambda e: e.nombre)]
        ],
        "fechas": [{"numero": n, "partidos": filas} for n, filas in sorted(fechas.items())],
        "eliminacion": [{"copa": copa, "partidos": filas} for copa, filas in copas.items()],
    }


def _volver(categoria: CategoriaNivel) -> HttpResponse:
    return redirect("categoria", pk=categoria.pk, pestana="fixture")


@require_POST
@requiere("torneo.configurar_torneo", "generar el fixture")
def generar(request: HttpRequest, pk: int) -> HttpResponse:
    categoria = get_object_or_404(CategoriaNivel.objects.select_related("torneo"), pk=pk)
    try:
        generar_fixture(categoria, nuevo_sorteo=bool(request.POST.get("nuevo_sorteo")))
    except FixtureNoSePuede as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Fixture de {categoria} listo")
    return _volver(categoria)


@require_POST
@requiere("torneo.configurar_torneo", "cambiar las series")
def guardar_series(request: HttpRequest, pk: int) -> HttpResponse:
    """Cambia equipos de serie y rehace el fixture con esas series (FIX-06)."""
    categoria = get_object_or_404(CategoriaNivel.objects.select_related("torneo"), pk=pk)
    asignacion = {
        int(clave.removeprefix("serie_")): request.POST.get(clave, "")
        for clave in request.POST
        if clave.startswith("serie_") and clave.removeprefix("serie_").isdigit()
    }
    try:
        generar_fixture(categoria, series=series_elegidas(categoria, asignacion))
    except FixtureNoSePuede as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Series de {categoria} guardadas y fixture rehecho")
    return _volver(categoria)


@require_POST
@requiere("torneo.configurar_torneo", "generar el fixture")
def generar_todos(request: HttpRequest, pk: int) -> HttpResponse:
    torneo = get_object_or_404(Torneo, pk=pk)
    resultado = generar_fixtures_faltantes(torneo)
    if resultado.generadas:
        cantidad = len(resultado.generadas)
        messages.success(
            request, f"Fixture de {cantidad} categoría{'s' if cantidad > 1 else ''} listo"
        )
    for _, problema in resultado.problemas:
        messages.warning(request, problema)
    return redirect("inicio")
