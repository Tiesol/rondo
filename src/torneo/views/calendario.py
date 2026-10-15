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

from dominio.config import Reglas
from dominio.franjas import proximo
from torneo.forms.reprogramar import FormularioSuspension
from torneo.models import Cancha, Club, Franja, Partido, Torneo
from torneo.permisos import requiere
from torneo.servicios.reprogramar import (
    Donde,
    donde_por_defecto,
    reanudar_dia,
    suspender_dia,
    vista_de_reanudar,
    vista_de_suspension,
)
from torneo.servicios.suspensiones import suspendidos_del_dia
from torneo.views.fixture import lado
from torneo.views.fragmentos import pide_fragmento

DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def _dias(torneo: Torneo) -> list[date]:
    """Los días de las franjas y también los de partidos ubicados a mano en un día sin franja
    (B9), por ejemplo un miércoles."""
    de_franjas = {timezone.localtime(f.inicio).date() for f in torneo.franjas.all()}
    de_partidos = {
        timezone.localtime(inicio).date()
        for inicio in Partido.objects.filter(
            categoria__torneo=torneo, inicio__isnull=False
        ).values_list("inicio", flat=True)
    }
    return sorted(de_franjas | de_partidos)


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
    suspendido = bool(franjas_del_dia) and all(f.suspendida for f in franjas_del_dia)
    contexto = {
        "es_dia_de_juego": bool(franjas_del_dia),
        "borrador": not torneo.publico,
        "suspendido": suspendido,
        # B3: lo que estaba en juego cuando se suspendió se muestra aparte; decide la organización.
        "en_juego": vista_de_suspension(torneo, dia).en_juego if suspendido else [],
        "form_dia": FormularioDia(
            torneo=torneo,
            initial={
                "dia": proximo(dia, Reglas.model_validate(torneo.reglas).dia_para_reprogramar),
                "desde": "17:00",
                "hasta": "20:00",
            },
        ),
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


@requiere("torneo.configurar_torneo", "suspender días")
def suspender(request: HttpRequest, fecha: str) -> HttpResponse:
    """B1 y B7: se dice qué se suspende y dónde se juega (por defecto, el próximo jueves de 16
    a 20), y se confirma. Nada se suspende con un solo toque."""
    torneo = Torneo.activo()
    if torneo is None:
        return redirect("inicio")
    try:
        dia = date.fromisoformat(fecha)
    except ValueError:
        raise Http404 from None
    vista = vista_de_suspension(torneo, dia)
    por_defecto = donde_por_defecto(torneo, dia)
    formulario = FormularioSuspension(
        request.POST if request.method == "POST" else None,
        torneo=torneo,
        initial=FormularioSuspension.inicial(por_defecto.dia, por_defecto.desde, por_defecto.hasta),
    )
    titulo_dia = f"{DIAS[dia.weekday()]} {dia.day}/{dia.month}"
    n = len(vista.se_suspenden)
    resumen = (
        f"Se suspenden los {n} partidos del {titulo_dia}."
        if n != 1
        else (f"Se suspende el partido del {titulo_dia}.")
    )
    if request.method == "POST" and formulario.is_valid() and request.POST.get("confirmado") == "1":
        datos = formulario.cleaned_data
        corrida = suspender_dia(
            torneo,
            dia,
            request.user,
            donde=Donde(datos["dia"], datos["desde"], datos["hasta"], list(datos["canchas"])),
            relajar=formulario.relajar(),
        )
        messages.success(request, "Día suspendido: sus partidos quedaron sin programar")
        return redirect("ver-propuestas", pk=corrida.pk)
    return render(
        request,
        "calendario/suspender.html",
        {
            "dia": dia,
            "titulo_dia": titulo_dia,
            "vista": vista,
            "resumen": resumen,
            "form": formulario,
        },
    )


@requiere("torneo.configurar_torneo", "reanudar días")
def reanudar(request: HttpRequest, fecha: str) -> HttpResponse:
    """B2: vuelve a abrir el día. Los que siguen sin lugar vuelven adonde estaban; los que ya se
    ubicaron en otro lado quedan donde están. Con confirmación (B7)."""
    torneo = Torneo.activo()
    if torneo is None:
        return redirect("inicio")
    try:
        dia = date.fromisoformat(fecha)
    except ValueError:
        raise Http404 from None
    vista = vista_de_reanudar(torneo, dia)
    titulo_dia = f"{DIAS[dia.weekday()]} {dia.day}/{dia.month}"
    detalle = [f"Vuelven a su lugar: {len(vista.vuelven)}"]
    if vista.en_otro_lado:
        detalle.append(f"Quedan donde están, ya reubicados: {len(vista.en_otro_lado)}")
    if vista.franja_extra is not None:
        detalle.append("Se quita el tiempo agregado al suspender, que quedó vacío")
    if request.method == "POST" and request.POST.get("confirmado") == "1":
        reanudar_dia(torneo, dia, request.user)
        messages.success(request, f"{titulo_dia} reanudado")
        return redirect("calendario-dia", fecha=dia.isoformat())
    return render(
        request,
        "calendario/reanudar.html",
        {"dia": dia, "titulo_dia": titulo_dia, "vista": vista, "detalle": detalle},
    )


class FormularioDia(forms.Form):
    dia = forms.DateField(
        label="Día", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
    )
    desde = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    hasta = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    canchas = forms.ModelMultipleChoiceField(
        queryset=Cancha.objects.none(),
        required=False,
        label="Canchas donde vale",
        help_text="Sin elegir: todas. Se usa solo si algo no entra en el horario normal.",
        widget=forms.CheckboxSelectMultiple,
        to_field_name="pk",
    )
    # T13.8 (P79): para que entre F11 se amplía C3 los fines de semana, no con jueves.
    fines_de_semana = forms.BooleanField(
        required=False,
        label="Repetir en todos los sábados y domingos del torneo",
        widget=forms.CheckboxInput(attrs={"role": "switch", "class": "interruptor"}),
    )

    def __init__(self, *args: Any, torneo: Torneo | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if torneo is not None:
            self.fields["canchas"].queryset = Cancha.objects.filter(  # type: ignore[attr-defined]
                torneo=torneo, padre__isnull=True
            )

    def clean(self) -> dict[str, Any]:
        datos = super().clean() or {}
        if datos.get("desde") and datos.get("hasta") and datos["hasta"] <= datos["desde"]:
            self.add_error("hasta", "Tiene que ser después de «desde».")
        return datos


@require_POST
@requiere("torneo.configurar_torneo", "agregar días")
def agregar_dia(request: HttpRequest) -> HttpResponse:
    """Cualquier día y horario para reprogramar (1.1), por ejemplo después de una lluvia."""
    torneo = Torneo.activo()
    formulario = FormularioDia(request.POST, torneo=torneo)
    if torneo is None or not formulario.is_valid():
        messages.error(request, "Revisa el día y el horario: el fin va después del inicio.")
        return redirect("calendario")
    datos = formulario.cleaned_data
    dias = dias_de_fin_de_semana(torneo) if datos["fines_de_semana"] else [datos["dia"]]
    for dia in dias:
        franja = Franja.objects.create(
            torneo=torneo,
            inicio=timezone.make_aware(datetime.combine(dia, datos["desde"])),
            fin=timezone.make_aware(datetime.combine(dia, datos["hasta"])),
            tipo=Franja.Tipo.ENTRE_SEMANA,
        )
        franja.canchas.set(datos["canchas"])
    cuantos = f" en {len(dias)} días" if len(dias) > 1 else ""
    messages.success(
        request, f"Tiempo agregado{cuantos}: se usa solo si algo no entra en el horario normal"
    )
    return redirect("calendario-dia", fecha=datos["dia"].isoformat())


def dias_de_fin_de_semana(torneo: Torneo) -> list[date]:
    """Los sábados y domingos con horario normal en el torneo (T13.8)."""
    return sorted(
        {
            timezone.localtime(f.inicio).date()
            for f in torneo.franjas.filter(tipo=Franja.Tipo.REGULAR)
            if timezone.localtime(f.inicio).weekday() >= 5
        }
    )


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
                "pk": partido.pk,
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
            "borrador": not torneo.publico,
            "dias": [
                {"titulo": f"{DIAS[d.weekday()]} {d.day}", "partidos": filas}
                for d, filas in dias.items()
            ],
        },
    )


@requiere("torneo.cargar_resultados", "ver los suspendidos")
def suspendidos(request: HttpRequest, fecha: str) -> HttpResponse:
    """T9.2: la lista de suspendidos del día, para la mesa."""
    torneo = Torneo.activo()
    if torneo is None:
        return redirect("inicio")
    try:
        dia = date.fromisoformat(fecha)
    except ValueError:
        raise Http404 from None
    contexto = {
        "dia": dia,
        "titulo_dia": f"{DIAS[dia.weekday()]} {dia.day}",
        "filas": suspendidos_del_dia(torneo, dia),
    }
    return render(request, "calendario/suspendidos.html", contexto)
