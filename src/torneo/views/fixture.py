"""Fixture de una categoría: series, partidos por fecha y eliminación (T3.5).

Lo que se muestra no tiene datos de personas: sirve igual para la página pública.
"""

from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
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
from torneo.servicios.programador import (
    calendario_actual,
    choques_del_calendario,
    partidos_del_torneo,
    problema_del_torneo,
)

COPAS = {"oro": "Copa de Oro", "plata": "Copa de Plata", "bronce": "Bronce"}


def lado(equipo: Equipo | None, texto: str) -> dict[str, Any]:
    if equipo is None:
        return {"nombre": texto, "escudo": None}
    return {"nombre": equipo.nombre, "escudo": escudo(equipo)}


def _cuando(partido: Partido) -> dict[str, str]:
    if partido.inicio is None:
        return {}
    local = timezone.localtime(partido.inicio)
    dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    return {
        "hora": local.strftime("%H:%M"),
        "dia": f"{dias[local.weekday()]} {local.day}",
        "cancha": partido.cancha.codigo if partido.cancha else "",
    }


def _fila(partido: Partido) -> dict[str, Any]:
    asignado = partido.local is not None or partido.visitante is not None
    return {
        "pk": partido.pk,
        "eliminacion": partido.fase == Partido.Fase.ELIMINACION,
        "local_id": partido.local_id,
        "visitante_id": partido.visitante_id,
        # P50: con los equipos asignados, la referencia ("1.º A vs 2.º B") sigue a la vista.
        "referencia": (
            f"{partido.texto_local} vs {partido.texto_visitante}"
            if asignado and partido.texto_local
            else ""
        ),
        "cuando": _cuando(partido),
        "local": lado(partido.local, partido.texto_local),
        "visitante": lado(partido.visitante, partido.texto_visitante),
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
        categoria.partidos.select_related("local", "visitante", "serie", "cancha").order_by(
            "fecha", "inicio", "pk"
        )
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
        "equipos": list(categoria.equipos.order_by("nombre")),
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


@require_POST
@requiere("torneo.configurar_torneo", "asignar los cruces")
def asignar(request: HttpRequest, pk: int) -> HttpResponse:
    """P50: el organizador asigna los participantes de un partido de eliminación."""
    partido = get_object_or_404(
        Partido.objects.select_related("categoria__torneo"), pk=pk, fase=Partido.Fase.ELIMINACION
    )
    categoria = partido.categoria
    elegidos = []
    for lado_ in ("local", "visitante"):
        valor = request.POST.get(lado_, "")
        equipo = (
            Equipo.objects.filter(pk=int(valor), categoria=categoria).first()
            if valor.isdigit()
            else None
        )
        if valor and equipo is None:
            messages.error(request, "Ese equipo no es de esta categoría.")
            return _volver(categoria)
        elegidos.append(equipo)
    local, visitante = elegidos
    if local is not None and local == visitante:
        messages.error(request, "Elige dos equipos distintos.")
        return _volver(categoria)
    partido.local, partido.visitante = local, visitante
    partido.save(update_fields=["local", "visitante"])
    messages.success(request, f"{partido.nombre}: equipos asignados")
    # Si ya estaba programado, con estos equipos puede chocar: se avisa (y se guarda igual).
    partidos = partidos_del_torneo(categoria.torneo)
    calendario = choques_del_calendario(
        problema_del_torneo(categoria.torneo, partidos), calendario_actual(partidos)
    )
    choques = [m for c in calendario if partido.pk in c.partidos for m in c.motivos]
    if choques:
        messages.warning(request, "Con estos equipos, el partido choca: " + "; ".join(choques))
    return _volver(categoria)
