"""Partidos de hoy (T11.11): la pantalla de la cancha en día de partido. Se recarga sola."""

from datetime import date

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from torneo.models import Torneo
from torneo.permisos import requiere
from torneo.servicios.hoy import partidos_de_hoy
from torneo.servicios.partido import cerrar_olvidados
from torneo.views.fragmentos import pide_fragmento


@requiere("torneo.cargar_resultados", "ver los partidos de hoy")
def hoy(request: HttpRequest) -> HttpResponse:
    torneo = Torneo.activo()
    if torneo is None:
        return redirect("inicio")
    try:
        dia = date.fromisoformat(request.GET.get("dia", ""))
    except ValueError:
        dia = timezone.localdate()
    cerrar_olvidados(torneo)  # T11.12
    contexto = {"dia": dia, "canchas": partidos_de_hoy(torneo, dia)}
    plantilla = "partidos/_hoy.html" if pide_fragmento(request) else "partidos/hoy.html"
    return render(request, plantilla, contexto)
