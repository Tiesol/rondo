"""Las imágenes se sirven desde la app (decisión del 2026-10-12): el bucket de R2 es privado y
el navegador nunca habla con él. Así cada imagen tiene su regla de acceso (T8.3).

Escudos, logo y patrocinadores no tienen datos personales: se ven sin login. La foto de una
persona (T8.4) se ve adentro de la app, para quien carga listas; afuera, solo si la familia la
autorizó (P66) y la persona está en un torneo con la página pública encendida. Si no, 404: no
se confirma ni que exista.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.db.models.fields.files import FieldFile
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST

from torneo.models import Club, Equipo, Organizador, Patrocinador, Persona
from torneo.permisos import requiere
from torneo.presentacion import olvidar_escudos
from torneo.servicios.imagenes import ImagenInvalida, quitar_imagen, reemplazar_imagen

UNA_HORA = 60 * 60


def _foto(request: HttpRequest, pk: int) -> FieldFile:
    persona = get_object_or_404(Persona, pk=pk)
    if request.user.has_perm("torneo.inscribir_equipos"):
        return persona.foto
    publica = persona.foto_autorizada and (
        persona.jugadores.filter(equipo__categoria__torneo__publico=True).exists()
        or persona.profes.filter(equipo__categoria__torneo__publico=True).exists()
    )
    if not publica:
        raise Http404
    return persona.foto


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
    campo = _foto(request, pk) if tipo == "foto" else _campo(tipo, pk)
    if not campo.name or not campo.storage.exists(campo.name):
        raise Http404
    with campo.open("rb") as archivo:
        respuesta = HttpResponse(archivo.read(), content_type="image/webp")
    # La URL lleva la versión (?v=): si la imagen cambia, cambia la URL. Una foto no se guarda
    # en cachés compartidas, y por poco tiempo: si se saca la autorización, deja de verse.
    if tipo == "foto":
        respuesta["Cache-Control"] = "private, max-age=60"
    else:
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
    if request.POST.get("volver") == "club":
        return redirect("club", pk=club.pk)
    equipo = Equipo.objects.filter(pk=request.POST.get("equipo") or 0, club=club).first()
    if equipo is not None:
        return redirect("equipo", pk=equipo.pk, seccion="plantel")
    return redirect("inicio")
