"""Calendario por día y cancha (T4.6). Sin datos de personas: solo equipos y horarios."""

from datetime import date, datetime, time, timedelta
from typing import Any

from django import forms
from django.contrib import messages
from django.db.models import Q
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from torneo.models import Cancha, Club, Franja, Partido, Torneo
from torneo.permisos import requiere
from torneo.servicios.reprogramar import suspender_dia
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
                "pk": partido.pk,
                "fijado": partido.fijado,
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
    franjas_del_dia = [
        f for f in torneo.franjas.all() if timezone.localtime(f.inicio).date() == dia
    ]
    contexto = {
        "es_dia_de_juego": bool(franjas_del_dia),
        "suspendido": bool(franjas_del_dia) and all(f.suspendida for f in franjas_del_dia),
        "form_dia": FormularioDia(initial={"dia": dia, "desde": "17:00", "hasta": "20:00"}),
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
        "clubes": Club.objects.filter(equipos__categoria__torneo=torneo)
        .distinct()
        .order_by("nombre"),
    }
    plantilla = "calendario/_dia.html" if pide_fragmento(request) else "calendario/dia.html"
    return render(request, plantilla, contexto)


@require_POST
@requiere("torneo.configurar_torneo", "suspender días")
def suspender(request: HttpRequest, fecha: str) -> HttpResponse:
    torneo = Torneo.activo()
    if torneo is None:
        return redirect("inicio")
    try:
        dia = date.fromisoformat(fecha)
    except ValueError:
        raise Http404 from None
    corrida = suspender_dia(torneo, dia, request.user)
    messages.success(request, "Día suspendido: sus partidos quedaron sin programar")
    return redirect("ver-propuestas", pk=corrida.pk)


class FormularioDia(forms.Form):
    dia = forms.DateField(label="Día", widget=forms.DateInput(attrs={"type": "date"}))
    desde = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    hasta = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))

    def clean(self) -> dict[str, Any]:
        datos = super().clean() or {}
        if datos.get("desde") and datos.get("hasta") and datos["hasta"] <= datos["desde"]:
            self.add_error("hasta", "Tiene que ser después de «desde».")
        return datos


@require_POST
@requiere("torneo.configurar_torneo", "agregar días")
def agregar_dia(request: HttpRequest) -> HttpResponse:
    """Un día entre semana para reprogramar (por ejemplo, después de una lluvia)."""
    torneo = Torneo.activo()
    formulario = FormularioDia(request.POST)
    if torneo is None or not formulario.is_valid():
        messages.error(request, "Revisa el día y el horario: el fin va después del inicio.")
        return redirect("calendario")
    dia = formulario.cleaned_data["dia"]
    Franja.objects.create(
        torneo=torneo,
        inicio=timezone.make_aware(datetime.combine(dia, formulario.cleaned_data["desde"])),
        fin=timezone.make_aware(datetime.combine(dia, formulario.cleaned_data["hasta"])),
        tipo=Franja.Tipo.ENTRE_SEMANA,
    )
    messages.success(request, "Día agregado: lo usan el programador y las propuestas")
    return redirect("calendario-dia", fecha=dia.isoformat())


def elegir_club(request: HttpRequest) -> HttpResponse:
    """El selector de club del calendario manda acá por GET."""
    club = request.GET.get("club", "")
    if not club.isdigit():
        return redirect("calendario")
    return redirect("calendario-club", pk=int(club))


def por_club(request: HttpRequest, pk: int) -> HttpResponse:
    """T5.7: todos los partidos de los equipos de un club, por día."""
    torneo = Torneo.activo()
    club = get_object_or_404(Club, pk=pk)
    if torneo is None:
        return redirect("inicio")
    partidos = (
        Partido.objects.filter(categoria__torneo=torneo, inicio__isnull=False)
        .filter(Q(local__club=club) | Q(visitante__club=club))
        .select_related("cancha", "local", "visitante", "categoria")
        .order_by("inicio")
    )
    dias: dict[date, list[dict[str, Any]]] = {}
    for partido in partidos:
        if partido.inicio is None:
            continue
        local = timezone.localtime(partido.inicio)
        dias.setdefault(local.date(), []).append(
            {
                "hora": f"{local:%H:%M}",
                "cancha": partido.cancha.codigo if partido.cancha else "",
                "categoria": str(partido.categoria),
                "nombre": partido.nombre,
                "local": lado(partido.local, partido.texto_local),
                "visitante": lado(partido.visitante, partido.texto_visitante),
            }
        )
    return render(
        request,
        "calendario/club.html",
        {
            "club": club,
            "dias": [
                {"titulo": f"{DIAS[d.weekday()]} {d.day}", "partidos": filas}
                for d, filas in dias.items()
            ],
        },
    )
