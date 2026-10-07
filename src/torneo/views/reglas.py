"""Reglas del torneo, con interruptores y números en lugar de JSON (TU.3)."""

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from torneo.forms.reglas import FormularioReglas
from torneo.models import Torneo
from torneo.permisos import requiere


@requiere("torneo.configurar_torneo", "cambiar las reglas")
def reglas(request: HttpRequest, pk: int) -> HttpResponse:
    torneo = get_object_or_404(Torneo, pk=pk)
    formulario = FormularioReglas(request.POST or None, initial=dict(torneo.reglas))
    if request.method == "POST" and formulario.is_valid():
        torneo.reglas = formulario.reglas.model_dump(mode="json")
        torneo.save()
        messages.success(request, "Reglas guardadas")
        return redirect("reglas", pk=torneo.pk)
    return render(request, "torneo/reglas.html", {"torneo": torneo, "form": formulario})
