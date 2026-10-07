"""Equipos: alta y ficha con su plantel y su cuerpo técnico (T2.5)."""

from typing import Any

from django.contrib import messages
from django.db.models import Count, Q, QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from torneo.forms.equipo import FormularioEquipo
from torneo.models import CategoriaNivel, Equipo
from torneo.permisos import requiere
from torneo.presentacion import escudo

SECCIONES = {"plantel": "Plantel", "cuerpo-tecnico": "Cuerpo técnico"}


def equipos_con_conteo(categoria: CategoriaNivel) -> QuerySet[Equipo]:
    """Los equipos de la categoría con `cantidad`, la cantidad de jugadores."""
    return (
        Equipo.objects.filter(categoria=categoria)
        .select_related("club")
        .annotate(cantidad=Count("jugadores"))
    )


def filas_de_equipos(categoria: CategoriaNivel) -> list[dict[str, Any]]:
    """La lista de la pestaña Equipos: cuántos jugadores tiene cada uno y si le faltan."""
    filas = []
    for equipo in equipos_con_conteo(categoria):
        cantidad: int = equipo.cantidad  # type: ignore[attr-defined]
        faltan = categoria.min_jugadores - cantidad
        filas.append(
            {
                "equipo": equipo,
                "escudo": escudo(equipo),
                "url": reverse("equipo", args=[equipo.pk, "plantel"]),
                "sub": f"{cantidad} de {categoria.max_jugadores} jugadores",
                "chip": f"Faltan {faltan}" if faltan > 0 else "",
            }
        )
    return filas


@requiere("torneo.inscribir_equipos", "cargar equipos")
def nuevo_equipo(request: HttpRequest, pk: int) -> HttpResponse:
    categoria = get_object_or_404(CategoriaNivel.objects.select_related("torneo"), pk=pk)
    formulario = FormularioEquipo(
        request.POST or None,
        torneo=categoria.torneo,
        initial={"categoria": categoria, "color_1": "#0d2440", "color_2": "#ffffff"},
    )
    if request.method == "POST" and formulario.is_valid():
        equipo = formulario.save()
        messages.success(request, f"Equipo «{equipo.nombre}» creado")
        return redirect("equipo", pk=equipo.pk, seccion="plantel")
    return render(request, "equipos/nuevo.html", {"form": formulario, "categoria": categoria})


def equipo(request: HttpRequest, pk: int, seccion: str) -> HttpResponse:
    if seccion not in SECCIONES:
        raise Http404
    actual = get_object_or_404(Equipo.objects.select_related("club", "categoria__torneo"), pk=pk)
    categoria = actual.categoria
    jugadores = actual.jugadores.select_related("persona").order_by("dorsal", "persona__apellidos")
    resumen = actual.jugadores.aggregate(
        total=Count("pk"),
        sin_verificar=Count("pk", filter=Q(verificado=False)),
        sin_dorsal=Count("pk", filter=Q(dorsal__isnull=True)),
        sin_documento=Count("pk", filter=Q(persona__clave_documento="")),
    )
    profes = actual.profes.select_related("persona").annotate(
        otros_equipos=Count("persona__profes") - 1
    )
    contexto = {
        "equipo": actual,
        "escudo": escudo(actual),
        "categoria": categoria,
        "seccion": seccion,
        "jugadores": jugadores,
        "profes": profes,
        "resumen": resumen,
        "completo": resumen["total"] >= categoria.min_jugadores,
        "pestanas": [
            {
                "texto": texto,
                "url": reverse("equipo", args=[actual.pk, clave]),
                "actual": clave == seccion,
            }
            for clave, texto in SECCIONES.items()
        ],
        "volver": reverse("categoria", args=[categoria.pk, "equipos"]),
    }
    return render(request, "equipos/ficha.html", contexto)
