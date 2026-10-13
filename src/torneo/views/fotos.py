"""Foto de una persona (jugador o profe) y la autorización de la familia (T8.4, P66 y P67).

La sube la organización o la mesa. El formulario pregunta si la familia la mandó para
publicarla: sin esa marca, la foto se ve solo adentro de la app. Quién la marcó y cuándo queda
registrado.
"""

import re

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from torneo.models import Equipo, Persona
from torneo.permisos import requiere
from torneo.presentacion import url_de_imagen
from torneo.servicios.imagenes import ImagenInvalida, quitar_imagen, reemplazar_imagen


def _volver_al_partido(request: HttpRequest) -> str:
    """T11.9: desde la planilla del partido, se vuelve a la ficha. Solo rutas de la app."""
    volver = request.POST.get("volver") or request.GET.get("volver") or ""
    return volver if re.fullmatch(r"/partidos/\d+/ficha/", volver) else ""


def _equipo(persona: Persona) -> Equipo | None:
    """El equipo para volver: el del jugador o, si es profe, el que dirige."""
    jugador = persona.jugadores.select_related("equipo").first()
    if jugador is not None:
        return jugador.equipo
    profe = persona.profes.select_related("equipo").first()
    return profe.equipo if profe is not None else None


@sensitive_variables()
@requiere("torneo.inscribir_equipos", "cargar fotos")
def foto(request: HttpRequest, pk: int) -> HttpResponse:
    persona = get_object_or_404(Persona, pk=pk)
    equipo = _equipo(persona)
    seccion = "plantel" if persona.jugadores.exists() else "cuerpo-tecnico"
    al_partido = _volver_al_partido(request)
    error = ""
    if request.method == "POST":
        try:
            if request.POST.get("quitar"):
                quitar_imagen(persona.foto)
                _autorizar(persona, request, autorizada=False)
                messages.success(request, "Foto quitada")
            else:
                if archivo := request.FILES.get("foto"):
                    reemplazar_imagen(persona.foto, archivo, tipo="foto")
                _autorizar(persona, request, autorizada=bool(request.POST.get("autorizada")))
                messages.success(request, "Foto guardada")
        except ImagenInvalida as problema:
            error = str(problema)
        else:
            if al_partido:
                return redirect(al_partido)
            if equipo is not None:
                return redirect("equipo", pk=equipo.pk, seccion=seccion)
            return redirect("foto-persona", pk=persona.pk)
    return render(
        request,
        "equipos/foto.html",
        {
            "persona": persona,
            "equipo": equipo,
            "volver": al_partido or (f"/equipos/{equipo.pk}/{seccion}/" if equipo else "/"),
            "al_partido": al_partido,
            "actual": url_de_imagen("foto", persona.pk, persona.foto.name),
            "error": error,
        },
    )


def _autorizar(persona: Persona, request: HttpRequest, *, autorizada: bool) -> None:
    """La autorización vale solo si hay foto. Si cambia, se registra quién y cuándo."""
    autorizada = autorizada and bool(persona.foto)
    if autorizada == persona.foto_autorizada:
        return
    persona.foto_autorizada = autorizada
    persona.foto_autorizada_por = request.user if autorizada else None  # type: ignore[assignment]
    persona.foto_autorizada_en = timezone.now() if autorizada else None
    persona.save(update_fields=["foto_autorizada", "foto_autorizada_por", "foto_autorizada_en"])
