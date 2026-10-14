"""Cambio manual verificado (T5.4)."""

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from torneo.forms.mover import FormularioMover
from torneo.models import Equipo, Partido
from torneo.permisos import requiere
from torneo.presentacion import cruce, lugar
from torneo.servicios.reprogramar import (
    ChoqueAlMover,
    candidatos_de_intercambio,
    mover_a_mano,
)
from torneo.servicios.reprogramar import intercambiar as intercambiar_partidos


@requiere("torneo.configurar_torneo", "mover partidos")
def mover(request: HttpRequest, pk: int) -> HttpResponse:
    partido = get_object_or_404(
        Partido.objects.select_related("categoria__torneo", "cancha", "local", "visitante"), pk=pk
    )
    formulario = FormularioMover(request.POST or None, partido=partido)
    motivos: list[str] = []
    bloquea = False
    if request.method == "POST" and formulario.is_valid():
        try:
            mover_a_mano(
                partido,
                formulario.cleaned_data["cancha"],
                formulario.inicio(),
                request.user,
                confirmar=request.POST.get("confirmar") == "1",
            )
        except ChoqueAlMover as error:
            motivos, bloquea = error.motivos, error.bloquea
        else:
            messages.success(request, "Partido movido")
            dia = timezone.localtime(formulario.inicio()).date().isoformat()
            return redirect("calendario-dia", fecha=dia)
    return render(
        request,
        "calendario/mover.html",
        {
            "partido": partido,
            "cruce": cruce(partido),
            "ahora": lugar(partido.inicio, partido.cancha.codigo if partido.cancha else ""),
            "form": formulario,
            "motivos": motivos,
            "bloquea": bloquea,
        },
    )


@requiere("torneo.configurar_torneo", "intercambiar partidos")
def intercambiar(request: HttpRequest, pk: int) -> HttpResponse:
    """B5: "Intercambiar con…". Los partidos de ese día y fin de semana en canchas compatibles,
    los que se pueden cambiar sin choques primero. Al elegir uno, los dos cambian en un paso."""
    partido = get_object_or_404(
        Partido.objects.select_related("categoria__torneo", "cancha", "local", "visitante"), pk=pk
    )
    motivos: list[str] = []
    elegido: Partido | None = None
    bloquea = False
    pidio = Equipo.objects.filter(
        pk=request.POST.get("pidio") or 0, pk__in=[partido.local_id, partido.visitante_id]
    ).first()
    if request.method == "POST":
        elegido = Partido.objects.filter(
            pk=request.POST.get("otro") or 0, categoria__torneo=partido.categoria.torneo
        ).first()
        if elegido is None:
            messages.error(request, "Elige con qué partido intercambiar.")
        else:
            try:
                intercambiar_partidos(
                    partido,
                    elegido,
                    request.user,
                    confirmar=request.POST.get("confirmar") == "1",
                    pidio=pidio,
                )
            except ChoqueAlMover as error:
                motivos, bloquea = error.motivos, error.bloquea
            else:
                messages.success(request, "Intercambiados")
                dia = timezone.localtime(partido.inicio).date().isoformat()
                return redirect("calendario-dia", fecha=dia)
    candidatos = [] if elegido and motivos else candidatos_de_intercambio(partido)
    return render(
        request,
        "calendario/intercambiar.html",
        {
            "partido": partido,
            "cruce": cruce(partido),
            "ahora": lugar(partido.inicio, partido.cancha.codigo if partido.cancha else ""),
            "candidatos": [
                {
                    "partido": c.partido,
                    "cruce": cruce(c.partido),
                    "lugar": lugar(
                        c.partido.inicio, c.partido.cancha.codigo if c.partido.cancha else ""
                    ),
                    "avisos": c.avisos,
                    "sin_choques": c.sin_choques,
                    "bloquea": c.bloquea,
                }
                for c in candidatos
            ],
            "elegido": elegido,
            "elegido_cruce": cruce(elegido) if elegido else "",
            "motivos": motivos,
            "bloquea": bloquea,
            "pidio": pidio,
            "equipos": [e for e in (partido.local, partido.visitante) if e is not None],
        },
    )
