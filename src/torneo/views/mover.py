"""Cambio manual verificado (T5.4)."""

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from torneo.forms.mover import FormularioMover
from torneo.models import Partido
from torneo.permisos import requiere
from torneo.presentacion import cruce, lugar
from torneo.servicios.reprogramar import ChoqueAlMover, mover_a_mano


@requiere("torneo.configurar_torneo", "mover partidos")
def mover(request: HttpRequest, pk: int) -> HttpResponse:
    partido = get_object_or_404(
        Partido.objects.select_related("categoria__torneo", "cancha", "local", "visitante"), pk=pk
    )
    formulario = FormularioMover(request.POST or None, partido=partido)
    motivos: list[str] = []
    if request.method == "POST" and formulario.is_valid():
        try:
            mover_a_mano(
                partido, formulario.cleaned_data["cancha"], formulario.inicio(), request.user
            )
        except ChoqueAlMover as error:
            motivos = error.motivos
        else:
            messages.success(request, "Partido movido y fijado")
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
        },
    )
