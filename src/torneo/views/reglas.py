"""Reglas del torneo, con interruptores y números en lugar de JSON (TU.3)."""

from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from dominio.config import describir_reglas
from torneo.forms.reglas import FormularioReglas
from torneo.models import Torneo
from torneo.permisos import requiere
from torneo.views.confirmar import confirmado, pedir_confirmacion


def _texto(valor: object) -> str:
    if valor is True:
        return "Sí"
    if valor is False:
        return "No"
    if valor in (None, ""):
        return "(vacío)"
    if isinstance(valor, list):
        return " y ".join(str(v) for v in valor)
    return str(valor)


def _cambios(antes: dict[str, Any], despues: dict[str, Any]) -> list[str]:
    """Qué cambió, en palabras: "Máximo de partidos por día: 2 → 3"."""
    return [
        f"{d.titulo}: {_texto(antes.get(d.nombre, d.defecto))} → {_texto(despues.get(d.nombre))}"
        for d in describir_reglas()
        if antes.get(d.nombre, d.defecto) != despues.get(d.nombre)
    ]


@requiere("torneo.configurar_torneo", "cambiar las reglas")
def reglas(request: HttpRequest, pk: int) -> HttpResponse:
    torneo = get_object_or_404(Torneo, pk=pk)
    formulario = FormularioReglas(request.POST or None, initial=dict(torneo.reglas))
    if request.method == "POST" and formulario.is_valid():
        nuevas = formulario.reglas.model_dump(mode="json")
        cambios = _cambios(torneo.reglas, nuevas)
        if not cambios:
            messages.info(request, "No cambiaste ninguna regla")
            return redirect("reglas", pk=torneo.pk)
        if not confirmado(request):
            return pedir_confirmacion(
                request,
                mensaje="Se cambia "
                + (f"{len(cambios)} reglas" if len(cambios) != 1 else "1 regla")
                + " del torneo.",
                detalle=cambios,
                boton="Guardar las reglas",
                volver=reverse("reglas", args=[torneo.pk]),
            )
        torneo.reglas = nuevas
        torneo.save()
        messages.success(request, "Reglas guardadas")
        return redirect("reglas", pk=torneo.pk)
    return render(request, "torneo/reglas.html", {"torneo": torneo, "form": formulario})
