"""Calendario por día y cancha (T4.6). Sin datos de personas: solo equipos y horarios."""

from datetime import date, datetime, time, timedelta
from typing import Any

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from torneo.models import Cancha, Partido, Torneo
from torneo.views.fixture import lado
from torneo.views.fragmentos import pide_fragmento

DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def _dias(torneo: Torneo) -> list[date]:
    return sorted({timezone.localtime(f.inicio).date() for f in torneo.franjas.all()})


def calendario(request: HttpRequest) -> HttpResponse:
    """Lleva al primer día con partidos, o al primero del torneo."""
    torneo = Torneo.activo()
    if torneo is None or not (dias := _dias(torneo)):
        return redirect("inicio")
    primero = (
        Partido.objects.filter(categoria__torneo=torneo, inicio__isnull=False)
        .order_by("inicio")
        .values_list("inicio", flat=True)
        .first()
    )
    dia = timezone.localtime(primero).date() if primero else dias[0]
    return redirect("calendario-dia", fecha=dia.isoformat())


def _del_dia(torneo: Torneo, dia: date) -> list[dict[str, Any]]:
    desde = timezone.make_aware(datetime.combine(dia, time.min))
    partidos = (
        Partido.objects.filter(
            categoria__torneo=torneo, inicio__gte=desde, inicio__lt=desde + timedelta(days=1)
        )
        .select_related("cancha__padre", "local", "visitante", "categoria")
        .order_by("inicio", "cancha__codigo")
    )
    canchas = Cancha.objects.filter(torneo=torneo, padre__isnull=True).order_by("codigo")
    secciones: dict[str, dict[str, Any]] = {
        c.codigo: {"nombre": c.nombre, "codigo": c.codigo, "partidos": []} for c in canchas
    }
    for partido in partidos:
        if partido.cancha is None or partido.inicio is None:
            continue
        entera = partido.cancha.padre or partido.cancha
        secciones[entera.codigo]["partidos"].append(
            {
                "hora": timezone.localtime(partido.inicio).strftime("%H:%M"),
                "categoria": str(partido.categoria),
                "mitad": partido.cancha.codigo if partido.cancha.padre else "",
                "nombre": partido.nombre,
                "local": lado(partido.local, partido.texto_local),
                "visitante": lado(partido.visitante, partido.texto_visitante),
            }
        )
    return list(secciones.values())


def calendario_dia(request: HttpRequest, fecha: str) -> HttpResponse:
    torneo = Torneo.activo()
    if torneo is None:
        return redirect("inicio")
    try:
        dia = date.fromisoformat(fecha)
    except ValueError:
        raise Http404 from None
    canchas = _del_dia(torneo, dia)
    contexto = {
        "torneo": torneo,
        "dia": dia,
        "titulo_dia": f"{DIAS[dia.weekday()]} {dia.day}",
        "dias": [
            {
                "corto": DIAS[d.weekday()],
                "numero": d.day,
                "url": reverse("calendario-dia", args=[d.isoformat()]),
                "actual": d == dia,
            }
            for d in _dias(torneo)
        ],
        "canchas": canchas,
        "hay_partidos": any(c["partidos"] for c in canchas),
    }
    plantilla = "calendario/_dia.html" if pide_fragmento(request) else "calendario/dia.html"
    return render(request, plantilla, contexto)
