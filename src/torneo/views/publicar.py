from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from torneo.models import Torneo
from torneo.permisos import requiere


@require_POST
@requiere("torneo.configurar_torneo", "publicar el torneo")
def publicar(request: HttpRequest, pk: int) -> HttpResponse:
    """Enciende o apaga la página pública del torneo."""
    torneo = get_object_or_404(Torneo, pk=pk)
    torneo.publico = not torneo.publico
    torneo.save(update_fields=["publico"])
    if torneo.publico:
        messages.success(request, f"La página pública de {torneo.nombre} ya se ve sin login")
    else:
        messages.success(request, f"La página pública de {torneo.nombre} dejó de verse")
    return redirect("mas")
