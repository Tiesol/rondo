from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from torneo.models import Torneo
from torneo.presentacion import edicion, fechas_del_torneo
from torneo.servicios.pendientes import pendientes


def inicio(request: HttpRequest) -> HttpResponse:
    torneo = Torneo.activo()
    contexto = {
        "torneo": torneo,
        "pendientes": pendientes(
            torneo, puede_configurar=request.user.has_perm("torneo.configurar_torneo")
        )
        if torneo
        else [],
        "antes": f"Torneo activo · {edicion(torneo)}" if torneo else "",
        "fechas": fechas_del_torneo(torneo) if torneo else "",
    }
    return render(request, "torneo/inicio.html", contexto)
