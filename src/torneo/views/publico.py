"""Página pública del torneo (TU.6, P53): sin login y nunca con datos personales.

Solo carga modelos sin datos de personas; lo controla tests/torneo/test_publico.py.
"""

from django.contrib.auth.decorators import login_not_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from torneo.models import CategoriaNivel, Torneo
from torneo.presentacion import fechas_del_torneo, resumen_de_categoria

PESTANAS = {"partidos": "Partidos", "posiciones": "Posiciones", "equipos": "Equipos"}


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
    plantilla = "publico/_categoria.html" if request.htmx else "publico/categoria.html"  # type: ignore[attr-defined]
    return render(request, plantilla, contexto)
