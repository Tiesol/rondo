"""Pantalla "Más": tu cuenta, las personas con su rol y los accesos de la organización."""

from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from torneo.permisos import MESA, ORGANIZACION, nombre_del_rol

ESTADO_DEL_ROL = {ORGANIZACION: "info", MESA: "neutro"}


def mas(request: HttpRequest) -> HttpResponse:
    personas = []
    for usuario in User.objects.filter(is_active=True).prefetch_related("groups"):
        rol = nombre_del_rol(usuario)
        personas.append(
            {
                "titulo": usuario.get_full_name() or usuario.username,
                "sub": usuario.username if usuario.get_full_name() else "",
                "chip": rol or "Sin rol",
                "chip_estado": ESTADO_DEL_ROL.get(rol, "aviso"),
            }
        )
    personas.sort(key=lambda p: p["titulo"].lower())
    return render(request, "torneo/mas.html", {"personas": personas})
