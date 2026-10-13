"""Página pública del torneo (TU.6, P53): sin login y nunca con datos personales.

Solo carga modelos sin datos de personas; lo controla tests/torneo/test_publico.py.
"""

from typing import Any

from django.contrib.auth.decorators import login_not_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from torneo.models import CategoriaNivel, Equipo, Partido, Torneo
from torneo.presentacion import escudo, fechas_del_torneo, resumen_de_categoria
from torneo.servicios.publico import (
    ficha_publica,
    goleadores,
    partidos_de,
    partidos_del_dia,
    patrocinadores_de,
    plantel_publico,
)
from torneo.servicios.tabla import tablas_de
from torneo.views.fragmentos import pide_fragmento

PESTANAS = {
    "partidos": "Partidos",
    "posiciones": "Posiciones",
    "goleadores": "Goleadores",
    "equipos": "Equipos",
}


# Las páginas públicas se guardan en la caché unos segundos (B7): con 1 CPU aguantan muchas
# visitas a la vez. Lo que cambia (un gol) aparece en menos de un minuto. El fragmento de HTMX
# y la página completa se guardan aparte.
CACHE_PUBLICA = 45


def _publica(vista: Any) -> Any:
    # Varía también por cookie: lo que ve alguien con sesión nunca se sirve a otro.
    return login_not_required(
        cache_page(CACHE_PUBLICA)(vary_on_headers("HX-Request", "Cookie")(vista))
    )


def _torneo_publico(pk: int) -> Torneo:
    return get_object_or_404(Torneo, pk=pk, publico=True)


@login_not_required
def publico(request: HttpRequest, pk: int) -> HttpResponse:
    torneo = _torneo_publico(pk)
    primera = torneo.categorias.first()
    if primera is None:
        raise Http404
    return redirect("publico-categoria", pk=torneo.pk, categoria=primera.pk, pestana="partidos")


@_publica
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
        "equipos": (
            [
                {
                    "nombre": e.nombre,
                    "club": e.club.nombre,
                    "escudo": escudo(e),
                    "url": reverse("publico-equipo", args=[torneo.pk, e.pk]),
                }
                for e in actual.equipos.select_related("club").order_by("nombre")
            ]
            if pestana == "equipos"
            else []
        ),
        "patrocinadores": patrocinadores_de(torneo),
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


@_publica
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
        "patrocinadores": patrocinadores_de(torneo),
    }
    return render(request, "publico/partido.html", contexto)


@_publica
def hoy(request: HttpRequest, pk: int) -> HttpResponse:
    """Los partidos de hoy de todo el torneo, en vivo."""
    torneo = _torneo_publico(pk)
    contexto = {
        "torneo": torneo,
        "fechas": fechas_del_torneo(torneo),
        "partidos": partidos_del_dia(torneo, timezone.localdate()),
        "patrocinadores": patrocinadores_de(torneo),
    }
    plantilla = "publico/_hoy.html" if pide_fragmento(request) else "publico/hoy.html"
    return render(request, plantilla, contexto)


@_publica
def equipo(request: HttpRequest, pk: int, equipo: int) -> HttpResponse:
    """El equipo con su escudo y su plantel: "Nombre I." y dorsal; la foto, si hay autorización."""
    torneo = _torneo_publico(pk)
    actual = get_object_or_404(
        Equipo.objects.select_related("club", "categoria"), pk=equipo, categoria__torneo=torneo
    )
    contexto = {
        "torneo": torneo,
        "equipo": {"nombre": actual.nombre, "club": actual.club.nombre, "escudo": escudo(actual)},
        "categoria": str(actual.categoria),
        "plantel": plantel_publico(actual),
        "volver": reverse("publico-categoria", args=[torneo.pk, actual.categoria_id, "equipos"]),
        "patrocinadores": patrocinadores_de(torneo),
    }
    return render(request, "publico/equipo.html", contexto)
