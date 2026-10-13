"""Alta de un jugador en la cancha (T11.9, P39): desde la planilla del partido, con la foto
de la cámara del celular. Corren las mismas reglas de inscripción, con sus avisos, y el jugador
queda jugando este partido con el dorsal que se escriba."""

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables

from dominio.inscripcion import Hallazgo
from torneo.forms.jugador import FormularioJugador
from torneo.models import Equipo, Partido
from torneo.permisos import requiere
from torneo.servicios import inscripcion, planilla
from torneo.servicios.imagenes import ImagenInvalida, reemplazar_imagen


@sensitive_post_parameters()
@sensitive_variables()
@requiere("torneo.inscribir_equipos", "inscribir jugadores")
def alta_rapida(request: HttpRequest, pk: int, equipo: int) -> HttpResponse:
    partido = get_object_or_404(Partido, pk=pk)
    del_partido = get_object_or_404(
        Equipo.objects.select_related("club", "categoria__torneo"),
        pk=equipo,
        pk__in=[partido.local_id, partido.visitante_id],
    )
    formulario = FormularioJugador(request.POST or None)
    hallazgos: list[Hallazgo] = []
    por_confirmar = False
    if request.method == "POST" and formulario.is_valid():
        dorsal = formulario.cleaned_data["dorsal"]
        resultado = inscripcion.agregar_jugador(
            del_partido,
            formulario.datos(),
            None,  # el habitual queda vacío: el dorsal es de este partido (P9)
            ahora=inscripcion.ahora_local(),
            confirmado=request.POST.get("confirmar") == "1",
        )
        if resultado.guardado and resultado.registro is not None:
            jugador = resultado.registro
            if archivo := request.FILES.get("foto"):
                try:
                    reemplazar_imagen(jugador.persona.foto, archivo, tipo="foto")
                except ImagenInvalida as error:
                    messages.warning(request, f"La foto no se guardó: {error}")
            try:
                planilla.cambiar_dorsal(partido, jugador, dorsal, request.user)  # type: ignore[arg-type]
            except planilla.NoSePuede as error:
                messages.warning(request, str(error))
            messages.success(request, f"{formulario.cleaned_data['nombres']} agregado y juega")
            for aviso in resultado.avisos:
                messages.warning(request, aviso.mensaje)
            return redirect("ficha-partido", pk=partido.pk)
        hallazgos, por_confirmar = resultado.hallazgos, resultado.por_confirmar
    return render(
        request,
        "partidos/alta.html",
        {
            "partido": partido,
            "equipo": del_partido,
            "form": formulario,
            "hallazgos": hallazgos,
            "por_confirmar": por_confirmar,
        },
    )
