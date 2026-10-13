"""Clubes (T11.6, P10): la organización los crea, los edita y une los duplicados."""

from django import forms
from django.contrib import messages
from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from torneo.models import Club
from torneo.permisos import requiere
from torneo.presentacion import olvidar_escudos, url_de_imagen
from torneo.servicios.clubes import NoSePuede, crear_club, editar_club, unir_clubes


class FormularioClub(forms.Form):
    nombre = forms.CharField(max_length=80)
    alias = forms.CharField(
        required=False,
        label="Otros nombres",
        help_text="Uno por línea. Sirven para reconocerlo al pegar listas.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )


@requiere("torneo.inscribir_equipos", "cambiar los clubes")
def clubes(request: HttpRequest) -> HttpResponse:
    formulario = FormularioClub(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        try:
            club = crear_club(formulario.cleaned_data["nombre"], formulario.cleaned_data["alias"])
        except NoSePuede as error:
            formulario.add_error("nombre", str(error))
        else:
            messages.success(request, f"{club} agregado")
            return redirect("clubes")
    lista = [
        {"club": c, "escudo": url_de_imagen("escudo", c.pk, c.escudo.name)}
        for c in Club.objects.annotate(cantidad=Count("equipos"))
    ]
    return render(request, "clubes/lista.html", {"lista": lista, "form": formulario})


@requiere("torneo.inscribir_equipos", "cambiar los clubes")
def club(request: HttpRequest, pk: int) -> HttpResponse:
    actual = get_object_or_404(Club, pk=pk)
    formulario = FormularioClub(
        request.POST or None,
        initial={"nombre": actual.nombre, "alias": "\n".join(actual.alias)},
    )
    if request.method == "POST" and formulario.is_valid():
        try:
            editar_club(actual, formulario.cleaned_data["nombre"], formulario.cleaned_data["alias"])
        except NoSePuede as error:
            formulario.add_error("nombre", str(error))
        else:
            messages.success(request, "Club guardado")
            return redirect("clubes")
    return render(
        request,
        "clubes/club.html",
        {
            "club": actual,
            "form": formulario,
            "escudo": url_de_imagen("escudo", actual.pk, actual.escudo.name),
            "equipos": actual.equipos.select_related("categoria"),
            "otros": Club.objects.exclude(pk=actual.pk),
        },
    )


@require_POST
@requiere("torneo.inscribir_equipos", "unir clubes")
def unir(request: HttpRequest, pk: int) -> HttpResponse:
    repetido = get_object_or_404(Club, pk=pk)
    destino = Club.objects.filter(pk=request.POST.get("destino") or 0).first()
    if destino is None:
        messages.error(request, "Elige con qué club unirlo.")
        return redirect("club", pk=pk)
    try:
        unir_clubes(repetido, destino)
    except NoSePuede as error:
        messages.error(request, str(error))
        return redirect("club", pk=pk)
    olvidar_escudos()
    messages.success(request, f"{repetido.nombre} unido a {destino.nombre}")
    return redirect("clubes")
