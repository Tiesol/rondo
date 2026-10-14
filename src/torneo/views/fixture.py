"""Fixture de una categoría: series, partidos por fecha y eliminación (T3.5).

Lo que se muestra no tiene datos de personas: sirve igual para la página pública.
"""

from datetime import datetime, time
from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from dominio.formatos import FormatoFaltante
from torneo.models import CategoriaNivel, Equipo, Partido, Torneo
from torneo.permisos import requiere
from torneo.presentacion import cruce, escudo
from torneo.servicios.cruces import aplicar, proponer
from torneo.servicios.fixture import (
    FixtureNoSePuede,
    formatos,
    generar_fixture,
    generar_fixtures_faltantes,
    motivo_desactualizado,
    rehacer_conservando,
    series_elegidas,
)
from torneo.servicios.partido import resultado_de
from torneo.servicios.programador import (
    calendario_actual,
    choques_del_calendario,
    partidos_del_torneo,
    problema_del_torneo,
)
from torneo.servicios.reprogramar import calcular_propuestas_en
from torneo.views.confirmar import confirmado, pedir_confirmacion

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


def datos_del_fixture(categoria: CategoriaNivel, *, con_propuesta: bool = False) -> dict[str, Any]:
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
    equipos = list(categoria.equipos.order_by("nombre"))
    fechas: dict[int, list[dict[str, Any]]] = {}
    copas: dict[str, list[dict[str, Any]]] = {}
    for partido in partidos:
        if partido.fase == Partido.Fase.GRUPOS and partido.fecha:
            fechas.setdefault(partido.fecha, []).append(_fila(partido))
        else:
            copas.setdefault(COPAS.get(partido.copa, partido.copa), []).append(_fila(partido))
    return {
        "problema": problema,
        "desactualizado": motivo_desactualizado(categoria, partidos, {e.pk for e in equipos}),
        "hay_jugados": any(p.empezado for p in partidos),
        "propuesta": _propuesta(categoria, partidos) if con_propuesta else None,
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
        "equipos": equipos,
    }


def _propuesta(categoria: CategoriaNivel, partidos: list[Partido]) -> dict[str, Any] | None:
    """T8.8: los cruces que salen de la tabla, si hay llaves sin asignar."""
    sin_asignar = [
        p for p in partidos if p.fase == Partido.Fase.ELIMINACION and not (p.local or p.visitante)
    ]
    if not sin_asignar:
        return None
    propuesta = proponer(categoria)
    return {
        "problema": propuesta.problema,
        "choques": propuesta.choques,
        "cruces": [
            {"nombre": p.nombre, "local": local.nombre, "visitante": visitante.nombre}
            for p, (local, visitante) in propuesta.cruces
        ],
    }


def _rehacer(categoria: CategoriaNivel) -> str:
    n = categoria.partidos.count()
    programados = categoria.partidos.filter(inicio__isnull=False).count()
    return (
        f"Se rehace el fixture de {categoria}: se borran sus {n} partidos"
        f"{f' ({programados} ya programados)' if programados else ''} y se arman de nuevo."
    )


def _volver(categoria: CategoriaNivel) -> HttpResponse:
    return redirect("categoria", pk=categoria.pk, pestana="fixture")


@require_POST
@requiere("torneo.configurar_torneo", "generar el fixture")
def generar(request: HttpRequest, pk: int) -> HttpResponse:
    categoria = get_object_or_404(CategoriaNivel.objects.select_related("torneo"), pk=pk)
    if categoria.partidos.exists() and not confirmado(request):
        return pedir_confirmacion(
            request,
            mensaje=_rehacer(categoria),
            boton="Rehacer el fixture",
            volver=reverse("categoria", args=[categoria.pk, "fixture"]),
            peligro=True,
        )
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
    if categoria.partidos.exists() and not confirmado(request):
        return pedir_confirmacion(
            request,
            mensaje=_rehacer(categoria),
            boton="Guardar las series",
            volver=reverse("categoria", args=[categoria.pk, "fixture"]),
            peligro=True,
        )
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


@require_POST
@requiere("torneo.configurar_torneo", "asignar los cruces")
def cruces(request: HttpRequest, pk: int) -> HttpResponse:
    """T8.8: asigna los cruces que salen de la tabla (P50). Si chocan, se avisa."""
    categoria = get_object_or_404(CategoriaNivel.objects.select_related("torneo"), pk=pk)
    propuesta = proponer(categoria)
    if propuesta.problema:
        messages.error(request, propuesta.problema)
        return _volver(categoria)
    cantidad = aplicar(categoria, propuesta)
    messages.success(request, f"Cruces asignados: {cantidad}")
    if propuesta.choques:
        messages.warning(request, "Con estos equipos, hay choques: " + "; ".join(propuesta.choques))
    return _volver(categoria)


@requiere("torneo.configurar_torneo", "rehacer el fixture")
def rehacer(request: HttpRequest, pk: int) -> HttpResponse:
    """T11.15 (P44, P80): rehacer con partidos jugados. Primero muestra qué se conserva, qué
    se borra y cuántos hay que programar; al confirmar, propone dónde ubicar los nuevos."""
    categoria = get_object_or_404(CategoriaNivel.objects.select_related("torneo"), pk=pk)
    try:
        vista = rehacer_conservando(categoria, aplicar=request.method == "POST")
    except FixtureNoSePuede as error:
        messages.error(request, str(error))
        return _volver(categoria)
    if request.method != "POST":
        return render(
            request,
            "fixture/rehacer.html",
            {
                "categoria": categoria,
                "conservados": [_resumen(p) for p in vista.conservados],
                "descartados": [_resumen(p) for p in vista.descartados],
                "nuevos": vista.nuevos,
            },
        )
    messages.success(request, f"Fixture de {categoria} rehecho")
    if not vista.nuevos:
        return _volver(categoria)
    torneo = categoria.torneo
    desde = timezone.localtime().replace(tzinfo=None)
    hasta = datetime.combine(torneo.fin, time.max)
    corrida = calcular_propuestas_en(
        torneo,
        desde,
        hasta,
        motivo=f"Fixture rehecho de {categoria}",
        origen={"categoria": categoria.pk},
        usuario=request.user,
    )
    return redirect("ver-propuestas", pk=corrida.pk)


def _resumen(partido: Partido) -> dict[str, str]:
    marcador = resultado_de(partido).marcador
    return {"cruce": cruce(partido), "marcador": f"{marcador[0]} a {marcador[1]}"}
