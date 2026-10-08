"""Propuestas de reprogramación (T5.3): verlas y aplicar una."""

from datetime import datetime
from typing import Any

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from torneo.models import Bloqueo, Corrida, Partido
from torneo.permisos import requiere
from torneo.presentacion import cruce, lugar
from torneo.servicios.reprogramar import NoSePuedeAplicar, aplicar, calcular_propuestas


def _lugar(guardado: list[str] | None) -> str:
    if guardado is None:
        return "Sin programar"
    codigo, cuando = guardado
    return lugar(timezone.make_aware(datetime.fromisoformat(cuando)), codigo)


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
        cantidad = len(propuesta)
        vista.append(
            {
                "indice": indice,
                "titulo": f"Mover {cantidad} partido{'s' if cantidad > 1 else ''}",
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
    return render(
        request,
        "reprogramar/propuestas.html",
        {"corrida": corrida, "propuestas": vista, "motivo": corrida.parametros.get("motivo", "")},
    )


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
