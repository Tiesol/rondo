"""Pantalla "Más": tu cuenta, las personas con su rol y los accesos de la organización."""

from typing import Any

from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from torneo.models import Cambio, Torneo
from torneo.permisos import MESA, ORGANIZACION, nombre_del_rol
from torneo.presentacion import cruce, lugar

ESTADO_DEL_ROL = {ORGANIZACION: "info", MESA: "neutro"}


def mas(request: HttpRequest) -> HttpResponse:
    personas: list[dict[str, Any]] = []
    for usuario in User.objects.filter(is_active=True).prefetch_related("groups"):
        rol = nombre_del_rol(usuario)
        personas.append(
            {
                "pk": usuario.pk,
                "rol": {ORGANIZACION: "organizacion", MESA: "mesa"}.get(rol, ""),
                "editable": usuario.pk != request.user.pk and not usuario.is_superuser,
                "titulo": usuario.get_full_name() or usuario.username,
                "sub": usuario.username if usuario.get_full_name() else "",
                "chip": rol or "Sin rol",
                "chip_estado": ESTADO_DEL_ROL.get(rol, "aviso"),
            }
        )
    personas.sort(key=lambda p: p["titulo"].lower())
    torneos = [
        {
            "pk": t.pk,
            "nombre": t.nombre,
            "fechas": f"Del {t.inicio:%d/%m} al {t.fin:%d/%m/%Y}",
            "publico": t.publico,
        }
        for t in Torneo.objects.order_by("-anio", "nombre")
    ]
    cambios = [
        {
            "cruce": f"{cruce(c.partido)} · {c.partido.categoria}",
            "antes": lugar(c.inicio_antes, c.cancha_antes.codigo if c.cancha_antes else ""),
            "despues": lugar(c.inicio_despues, c.cancha_despues.codigo if c.cancha_despues else ""),
            "quien": c.usuario.get_full_name() or c.usuario.username if c.usuario else "",
            "cuando": c.fecha,
            "motivo": c.motivo,
        }
        for c in Cambio.objects.select_related(
            "partido__local",
            "partido__visitante",
            "partido__categoria",
            "cancha_antes",
            "cancha_despues",
            "usuario",
        )[:10]
    ]
    return render(
        request,
        "torneo/mas.html",
        {"personas": personas, "torneos": torneos, "cambios": cambios},
    )
