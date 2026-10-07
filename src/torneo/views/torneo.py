"""Pantalla Torneo: una categoría-nivel con sus pestañas (TU.5).

Cambiar de categoría o de pestaña usa HTMX: con HX-Request se devuelve solo #categoria y la
URL se actualiza (hx-push-url), así se puede compartir o volver atrás.
"""

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from torneo.forms.categoria import FormularioAjustes
from torneo.models import CategoriaNivel, Torneo
from torneo.permisos import sin_permiso
from torneo.presentacion import nacidos_en, resumen_de_categoria
from torneo.views.equipos import filas_de_equipos
from torneo.views.fragmentos import pide_fragmento

PESTANAS = {
    "equipos": "Equipos",
    "fixture": "Fixture",
    "posiciones": "Posiciones",
    "ajustes": "Ajustes",
}


def torneo(request: HttpRequest) -> HttpResponse:
    activo = Torneo.activo()
    primera = activo.categorias.first() if activo else None
    if primera is None:
        return redirect("inicio")
    return redirect("categoria", pk=primera.pk, pestana="equipos")


def categoria(request: HttpRequest, pk: int, pestana: str) -> HttpResponse:
    if pestana not in PESTANAS:
        raise Http404
    actual = get_object_or_404(CategoriaNivel.objects.select_related("torneo"), pk=pk)
    puede_cambiar = request.user.has_perm("torneo.configurar_torneo")

    formulario = None
    if pestana == "ajustes":
        if request.method == "POST" and not puede_cambiar:
            return sin_permiso(request, "cambiar los ajustes de una categoría")
        if puede_cambiar:
            formulario = FormularioAjustes(request.POST or None, instance=actual)
            if request.method == "POST" and formulario.is_valid():
                formulario.save()
                messages.success(request, f"Ajustes de {actual} guardados")
                return redirect("categoria", pk=actual.pk, pestana="ajustes")

    contexto = {
        "categoria": actual,
        "nombre": str(actual),
        "pestana": pestana,
        "resumen": resumen_de_categoria(actual),
        "nacidos": nacidos_en(actual),
        "canchas": " o ".join(c.codigo for c in actual.canchas.all()) or "Ninguna",
        "nivel": "" if actual.nivel == CategoriaNivel.Nivel.UNICO else actual.get_nivel_display(),
        "categorias": [
            {
                "texto": str(c),
                "url": reverse("categoria", args=[c.pk, pestana]),
                "actual": c.pk == actual.pk,
            }
            for c in actual.torneo.categorias.all()
        ],
        "pestanas": [
            {
                "texto": texto,
                "url": reverse("categoria", args=[actual.pk, clave]),
                "actual": clave == pestana,
            }
            for clave, texto in PESTANAS.items()
        ],
        "form": formulario,
        "puede_cambiar": puede_cambiar,
        "equipos": filas_de_equipos(actual) if pestana == "equipos" else [],
    }
    plantilla = "torneo/_categoria.html" if pide_fragmento(request) else "torneo/categoria.html"
    return render(request, plantilla, contexto)
