"""Datos de la escuela: nombre y colores del organizador, sin admin (TU.7)."""

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from torneo.forms.escuela import FormularioEscuela
from torneo.models import Organizador
from torneo.permisos import requiere


@requiere("torneo.configurar_torneo", "cambiar los datos de la escuela")
def escuela(request: HttpRequest) -> HttpResponse:
    formulario = FormularioEscuela(request.POST or None, instance=Organizador.actual())
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(request, "Datos de la escuela guardados")
        return redirect("escuela")
    return render(request, "torneo/escuela.html", {"form": formulario})
