"""Página pública del torneo (TU.6, P53): sin login y nunca con datos personales.

Solo carga modelos sin datos de personas; lo controla tests/torneo/test_publico.py.
"""

from django.contrib.auth.decorators import login_not_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from torneo.models import CategoriaNivel, Partido, Torneo
from torneo.presentacion import fechas_del_torneo, resumen_de_categoria
from torneo.servicios.publico import ficha_publica, goleadores, partidos_de, partidos_del_dia
from torneo.servicios.tabla import tablas_de
from torneo.views.fragmentos import pide_fragmento

PESTANAS = {
    "partidos": "Partidos",
    "posiciones": "Posiciones",
    "goleadores": "Goleadores",
    "equipos": "Equipos",
}


def _torneo_publico(pk: int) -> Torneo:
    return get_object_or_404(Torneo, pk=pk, publico=True)


@login_not_required
def publico(request: HttpRequest, pk: int) -> HttpResponse:
    torneo = _torneo_publico(pk)
    primera = torneo.categorias.first()
    if primera is None:
        raise Http404
    return redirect("publico-categoria", pk=torneo.pk, categoria=primera.pk, pestana="partidos")


@login_not_required
def categoria(request: HttpRequest, pk: int, categoria: int, pestana: str) -> HttpResponse:
    if pestana not in PESTANAS:
        raise Http404
    torneo = _torneo_publico(pk)
    actual = get_object_or_404(CategoriaNivel, pk=categoria, torneo=torneo)
    contexto = {
        "torneo": torneo,
        "fechas": fechas_del_torneo(torneo),
        "categoria": actual,
        "nombre": str(actual),
        "resumen": resumen_de_categoria(actual),
        "pestana": pestana,
        "partidos": partidos_de(actual) if pestana == "partidos" else [],
        "tablas": tablas_de(actual) if pestana == "posiciones" else [],
        "goleadores": goleadores(actual) if pestana == "goleadores" else [],
        "equipos": list(actual.equipos.select_related("club")) if pestana == "equipos" else [],
        "categorias": [
            {
                "texto": str(c),
                "url": reverse("publico-categoria", args=[torneo.pk, c.pk, pestana]),
                "actual": c.pk == actual.pk,
            }
            for c in torneo.categorias.all()
        ],
        "pestanas": [
            {
                "texto": texto,
                "url": reverse("publico-categoria", args=[torneo.pk, actual.pk, clave]),
                "actual": clave == pestana,
            }
            for clave, texto in PESTANAS.items()
        ],
    }
    plantilla = "publico/_categoria.html" if pide_fragmento(request) else "publico/categoria.html"
    return render(request, plantilla, contexto)


@login_not_required
def partido(request: HttpRequest, pk: int, partido: int) -> HttpResponse:
    """La ficha pública: goles, tarjetas y mejor jugador (P70), con "Nombre I." (P65)."""
    torneo = _torneo_publico(pk)
    actual = get_object_or_404(
        Partido.objects.select_related("categoria__torneo", "local__club", "visitante__club"),
        pk=partido,
        categoria__torneo=torneo,
    )
    contexto = {
        "torneo": torneo,
        "fechas": fechas_del_torneo(torneo),
        "ficha": ficha_publica(actual),
        "volver": reverse("publico-categoria", args=[torneo.pk, actual.categoria_id, "partidos"]),
    }
    return render(request, "publico/partido.html", contexto)


@login_not_required
def hoy(request: HttpRequest, pk: int) -> HttpResponse:
    """Los partidos de hoy de todo el torneo, en vivo."""
    torneo = _torneo_publico(pk)
    contexto = {
        "torneo": torneo,
        "fechas": fechas_del_torneo(torneo),
        "partidos": partidos_del_dia(torneo, timezone.localdate()),
    }
    plantilla = "publico/_hoy.html" if pide_fragmento(request) else "publico/hoy.html"
    return render(request, plantilla, contexto)
