"""Las imágenes se sirven desde la app (decisión del 2026-10-12): el bucket de R2 es privado y
el navegador nunca habla con él. Así cada imagen tiene su regla de acceso (T8.3).

Escudos, logo y patrocinadores no tienen datos personales: se ven sin login.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.db.models.fields.files import FieldFile
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST

from torneo.models import Club, Equipo, Organizador, Patrocinador
from torneo.permisos import requiere
from torneo.presentacion import olvidar_escudos
from torneo.servicios.imagenes import ImagenInvalida, quitar_imagen, reemplazar_imagen

UNA_HORA = 60 * 60


def _campo(tipo: str, pk: int) -> FieldFile:
    match tipo:
        case "escudo":
            return get_object_or_404(Club, pk=pk).escudo
        case "logo":
            return Organizador.actual().logo
        case "patrocinador":
            return get_object_or_404(Patrocinador, pk=pk).imagen
    raise Http404


@login_not_required
@require_GET
def imagen(request: HttpRequest, tipo: str, pk: int) -> HttpResponse:
    campo = _campo(tipo, pk)
    if not campo.name or not campo.storage.exists(campo.name):
        raise Http404
    with campo.open("rb") as archivo:
        respuesta = HttpResponse(archivo.read(), content_type="image/webp")
    # La URL lleva la versión (?v=): si la imagen cambia, cambia la URL.
    respuesta["Cache-Control"] = f"public, max-age={UNA_HORA}"
    return respuesta


@require_POST
@requiere("torneo.configurar_torneo", "cambiar los escudos")
def escudo(request: HttpRequest, pk: int) -> HttpResponse:
    club = get_object_or_404(Club, pk=pk)
    try:
        if request.POST.get("quitar"):
            quitar_imagen(club.escudo)
            messages.success(request, f"Escudo de {club} quitado")
        elif archivo := request.FILES.get("escudo"):
            reemplazar_imagen(club.escudo, archivo, tipo="escudo")
            messages.success(request, f"Escudo de {club} guardado: aparece en todos sus equipos")
        else:
            messages.error(request, "Elige la imagen del escudo.")
    except ImagenInvalida as error:
        messages.error(request, str(error))
    olvidar_escudos()
    equipo = Equipo.objects.filter(pk=request.POST.get("equipo") or 0, club=club).first()
    if equipo is not None:
        return redirect("equipo", pk=equipo.pk, seccion="plantel")
    return redirect("inicio")
