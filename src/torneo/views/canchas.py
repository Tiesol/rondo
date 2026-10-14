"""Pantalla de canchas del torneo (T10.5; P13, P63). Solo para quien configura el torneo."""

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from torneo.models import Cancha, Torneo
from torneo.permisos import requiere
from torneo.servicios import canchas as servicio
from torneo.views.confirmar import confirmado, pedir_confirmacion

_QUE = "cambiar las canchas"


@requiere("torneo.configurar_torneo", _QUE)
def canchas(request: HttpRequest, pk: int) -> HttpResponse:
    torneo = get_object_or_404(Torneo, pk=pk)
    enteras = Cancha.objects.filter(torneo=torneo, padre__isnull=True).prefetch_related("mitades")
    return render(request, "torneo/canchas.html", {"torneo": torneo, "canchas": enteras})


@require_POST
@requiere("torneo.configurar_torneo", _QUE)
def agregar(request: HttpRequest, pk: int) -> HttpResponse:
    torneo = get_object_or_404(Torneo, pk=pk)
    nueva = servicio.agregar_cancha(torneo)
    messages.success(request, f"{nueva.nombre} agregada: elige en los ajustes quién juega ahí")
    return redirect("canchas", pk=torneo.pk)


@require_POST
@requiere("torneo.configurar_torneo", _QUE)
def accion(request: HttpRequest, pk: int, cancha: int, que: str) -> HttpResponse:
    actual = get_object_or_404(Cancha, pk=cancha, torneo_id=pk)
    acciones = {"partir": servicio.partir, "unir": servicio.unir, "quitar": servicio.quitar}
    if que not in acciones:
        messages.error(request, "Acción desconocida.")
        return redirect("canchas", pk=pk)
    if que in ("unir", "quitar") and not confirmado(request):
        mensaje = (
            f"Se unen las mitades de {actual.nombre}."
            if que == "unir"
            else f"Se quita {actual.nombre} del torneo."
        )
        return pedir_confirmacion(
            request,
            mensaje=mensaje,
            boton="Unir" if que == "unir" else "Quitar",
            volver=reverse("canchas", args=[pk]),
            peligro=True,
        )
    try:
        acciones[que](actual)
    except servicio.NoSePuede as error:
        messages.error(request, str(error))
    else:
        textos = {"partir": "partida en dos mitades", "unir": "unida", "quitar": "quitada"}
        messages.success(request, f"{actual.nombre} {textos[que]}")
    return redirect("canchas", pk=pk)
