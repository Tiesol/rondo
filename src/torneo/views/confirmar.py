"""Un solo "¿Estás seguro?" para lo importante (B7, fase 12).

Una acción importante llega por POST. Si todavía no trae `confirmado=1`, no se hace: se muestra
una pantalla que dice qué va a pasar ("Se suspenden los 26 partidos del sábado 31/10"), con los
mismos datos escondidos y el botón para confirmar. Funciona sin JavaScript. También con HTMX:
la respuesta reemplaza lo que se iba a reemplazar.
"""

from collections.abc import Sequence

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from torneo.views.fragmentos import pide_fragmento


def confirmado(request: HttpRequest) -> bool:
    return request.method == "POST" and request.POST.get("confirmado") == "1"


def pedir_confirmacion(
    request: HttpRequest,
    *,
    mensaje: str,
    boton: str = "Confirmar",
    detalle: Sequence[str] = (),
    volver: str = "/",
    peligro: bool = False,
    destino: str = "",
) -> HttpResponse:
    """La pantalla de confirmación para este POST. `destino` es el id que HTMX reemplaza."""
    campos = [
        (clave, valor)
        for clave, valores in request.POST.lists()
        for valor in valores
        if clave not in ("csrfmiddlewaretoken", "confirmado")
    ]
    plantilla = "parciales/_confirmar.html" if pide_fragmento(request) else "confirmar.html"
    return render(
        request,
        plantilla,
        {
            "mensaje": mensaje,
            "boton": boton,
            "detalle": list(detalle),
            "volver": volver,
            "peligro": peligro,
            "campos": campos,
            "destino": destino,
            "accion": request.path,
        },
    )
