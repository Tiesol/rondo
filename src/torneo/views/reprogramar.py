"""Propuestas de reprogramación (T5.3): verlas y aplicar una."""

from datetime import datetime
from typing import Any

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from dominio.partido import Lado
from torneo.models import Bloqueo, Corrida, Partido
from torneo.permisos import requiere
from torneo.presentacion import cruce, lugar
from torneo.servicios.partido import NoSePuede, wo
from torneo.servicios.reprogramar import (
    NoSePuedeAplicar,
    afectados_por,
    aplicar,
    calcular_propuestas,
    veces_que_reprogramo,
)


def _lugar(guardado: list[str] | None) -> str:
    if guardado is None:
        return "Sin programar"
    codigo, cuando = guardado
    return lugar(timezone.make_aware(datetime.fromisoformat(cuando)), codigo)


def _titulo(propuesta: list[dict[str, Any]]) -> str:
    """ "Mover 2 partidos", "Ubicar 3 partidos" o "Ubicar 3 y mover 1"."""
    ubicar = sum(1 for m in propuesta if m["antes"] is None)
    mover = len(propuesta) - ubicar

    def partidos(n: int) -> str:
        return f"{n} partido{'s' if n != 1 else ''}"

    if ubicar and mover:
        return f"Ubicar {ubicar} y mover {mover}"
    return f"Ubicar {partidos(ubicar)}" if ubicar else f"Mover {partidos(mover)}"


@require_POST
@requiere("torneo.configurar_torneo", "reprogramar")
def propuestas(request: HttpRequest, pk: int) -> HttpResponse:
    bloqueo = get_object_or_404(Bloqueo.objects.select_related("torneo"), pk=pk)
    corrida = calcular_propuestas(bloqueo, request.user)
    return redirect("ver-propuestas", pk=corrida.pk)


@requiere("torneo.configurar_torneo", "reprogramar")
def ver_propuestas(request: HttpRequest, pk: int) -> HttpResponse:
    corrida = get_object_or_404(Corrida, pk=pk, tipo=Corrida.Tipo.REPROGRAMAR)
    guardadas = corrida.resultado.get("propuestas", [])
    ids = {m["partido"] for propuesta in guardadas for m in propuesta}
    partidos = {
        p.pk: p
        for p in Partido.objects.filter(pk__in=ids).select_related(
            "local", "visitante", "categoria"
        )
    }
    vista: list[dict[str, Any]] = []
    for indice, propuesta in enumerate(guardadas):
        vista.append(
            {
                "indice": indice,
                "titulo": _titulo(propuesta),
                "movimientos": [
                    {
                        "antes": _lugar(m["antes"]),
                        "despues": _lugar(m["despues"]),
                        "cruce": cruce(partidos[m["partido"]]),
                        "categoria": str(partidos[m["partido"]].categoria),
                    }
                    for m in propuesta
                    if m["partido"] in partidos
                ],
            }
        )
    pedido = Bloqueo.objects.filter(pk=corrida.parametros.get("bloqueo")).first()
    afectados = afectados_por(pedido) if pedido else []
    veces = {e.pk: veces_que_reprogramo(e) for e in (pedido.equipos.all() if pedido else [])}
    return render(
        request,
        "reprogramar/propuestas.html",
        {
            "corrida": corrida,
            "propuestas": vista,
            "motivo": corrida.parametros.get("motivo", ""),
            # T10.10: dar W.O. en lugar de reprogramar, y cuántas veces ya reprogramó.
            "afectados": [
                {
                    "partido": p,
                    "equipo": e,
                    "cruce": cruce(p),
                    "aviso": _ya_reprogramo(e.nombre, veces.get(e.pk, 0)),
                }
                for p, e in afectados
            ],
        },
    )


def _ya_reprogramo(nombre: str, veces: int) -> str:
    """ "River ya reprogramó 2 veces": sin límite, la organización decide (T10.10)."""
    if not veces:
        return ""
    return f"{nombre} ya reprogramó {veces} {'vez' if veces == 1 else 'veces'}."


@require_POST
@requiere("torneo.configurar_torneo", "reprogramar")
def dar_wo(request: HttpRequest, pk: int) -> HttpResponse:
    """T10.10: el equipo que pidió reprogramar pierde el partido por W.O."""
    corrida = get_object_or_404(Corrida, pk=pk, tipo=Corrida.Tipo.REPROGRAMAR)
    pedido = get_object_or_404(Bloqueo, pk=corrida.parametros.get("bloqueo"))
    elegido = next(
        (
            (p, e)
            for p, e in afectados_por(pedido)
            if str(p.pk) == request.POST.get("partido") and str(e.pk) == request.POST.get("equipo")
        ),
        None,
    )
    if elegido is None:
        messages.error(request, "Ese partido no es del pedido.")
        return redirect("ver-propuestas", pk=corrida.pk)
    partido, equipo = elegido
    lado: Lado = "local" if partido.local_id == equipo.pk else "visitante"
    try:
        wo(partido, lado, request.user)
    except NoSePuede as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"W.O.: {equipo.nombre} pierde {cruce(partido)}")
    return redirect("ver-propuestas", pk=corrida.pk)


@require_POST
@requiere("torneo.configurar_torneo", "reprogramar")
def aplicar_propuesta(request: HttpRequest, pk: int, indice: int) -> HttpResponse:
    corrida = get_object_or_404(Corrida, pk=pk, tipo=Corrida.Tipo.REPROGRAMAR)
    if not 0 <= indice < len(corrida.resultado.get("propuestas", [])):
        raise Http404
    try:
        cambios = aplicar(corrida, indice, request.user)
    except NoSePuedeAplicar as error:
        messages.error(request, str(error))
        return redirect("ver-propuestas", pk=corrida.pk)
    messages.success(request, f"Propuesta aplicada: {len(cambios)} partido(s) movido(s)")
    primero = min((c.inicio_despues for c in cambios if c.inicio_despues), default=None)
    if primero:
        return redirect("calendario-dia", fecha=timezone.localtime(primero).date().isoformat())
    return redirect("calendario")
