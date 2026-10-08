"""Partido de la ACF (T5.1): cargar un bloqueo y ver qué partidos chocan."""

from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from torneo.forms.bloqueo import FormularioBloqueo
from torneo.models import Bloqueo, Partido, Torneo
from torneo.permisos import requiere
from torneo.servicios.bloqueos import partidos_que_chocan

DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def describir(partido: Partido) -> dict[str, str]:
    """Un partido programado en una línea, sin datos de personas."""
    assert partido.inicio is not None
    local = timezone.localtime(partido.inicio)
    equipos = " vs ".join(
        e.nombre if e else texto
        for e, texto in (
            (partido.local, partido.texto_local),
            (partido.visitante, partido.texto_visitante),
        )
    )
    return {
        "cuando": f"{DIAS[local.weekday()]} {local.day} · {local:%H:%M} · "
        f"{partido.cancha.codigo if partido.cancha else ''}",
        "cruce": equipos,
        "categoria": str(partido.categoria),
    }


def _bloqueos(torneo: Torneo) -> list[dict[str, Any]]:
    filas = []
    for bloqueo in Bloqueo.objects.filter(torneo=torneo).prefetch_related("equipos__categoria"):
        equipos = list(bloqueo.equipos.all())
        inicio, fin = timezone.localtime(bloqueo.inicio), timezone.localtime(bloqueo.fin)
        filas.append(
            {
                "bloqueo": bloqueo,
                "cuando": f"{DIAS[inicio.weekday()]} {inicio.day} · {inicio:%H:%M} a {fin:%H:%M}",
                "equipos": ", ".join(f"{e.nombre} ({e.categoria})" for e in equipos),
                "choques": [
                    describir(p)
                    for p in partidos_que_chocan(torneo, equipos, bloqueo.inicio, bloqueo.fin)
                ],
            }
        )
    return filas


@requiere("torneo.configurar_torneo", "cargar partidos de la ACF")
def acf(request: HttpRequest, pk: int) -> HttpResponse:
    torneo = get_object_or_404(Torneo, pk=pk)
    formulario = FormularioBloqueo(request.POST or None, torneo=torneo)
    if request.method == "POST" and formulario.is_valid():
        bloqueo = Bloqueo.objects.create(
            torneo=torneo,
            inicio=formulario.momento("desde"),
            fin=formulario.momento("hasta"),
            motivo=formulario.cleaned_data["motivo"],
        )
        bloqueo.equipos.set(formulario.cleaned_data["equipos"])
        messages.success(request, "Bloqueo guardado")
        return redirect("acf", pk=torneo.pk)
    return render(
        request,
        "acf/acf.html",
        {"torneo": torneo, "form": formulario, "bloqueos": _bloqueos(torneo)},
    )


@require_POST
@requiere("torneo.configurar_torneo", "cargar partidos de la ACF")
def revisar(request: HttpRequest, pk: int) -> HttpResponse:
    """En vivo, sin guardar: qué partidos programados chocarían con este bloqueo."""
    torneo = get_object_or_404(Torneo, pk=pk)
    formulario = FormularioBloqueo(request.POST, torneo=torneo)
    choques = None
    if formulario.is_valid():
        inicio, fin = formulario.momento("desde"), formulario.momento("hasta")
        choques = [
            describir(p)
            for p in partidos_que_chocan(torneo, formulario.cleaned_data["equipos"], inicio, fin)
        ]
    return render(request, "acf/_choques.html", {"choques": choques})


@require_POST
@requiere("torneo.configurar_torneo", "cargar partidos de la ACF")
def borrar(request: HttpRequest, pk: int) -> HttpResponse:
    bloqueo = get_object_or_404(Bloqueo, pk=pk)
    torneo_pk = bloqueo.torneo_id
    bloqueo.delete()
    messages.success(request, "Bloqueo borrado")
    return redirect("acf", pk=torneo_pk)
