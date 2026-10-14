"""Patrocinadores del torneo (P69, T8.3): imagen, nombre y orden. Solo la organización."""

from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from torneo.models import Patrocinador, Torneo
from torneo.permisos import requiere
from torneo.presentacion import url_de_imagen
from torneo.servicios.imagenes import ImagenInvalida, SinAlmacenamiento, procesar_imagen
from torneo.views.confirmar import confirmado, pedir_confirmacion


class FormularioPatrocinador(forms.Form):
    nombre = forms.CharField(max_length=80)
    orden = forms.IntegerField(min_value=0, max_value=99, initial=0)


@requiere("torneo.configurar_torneo", "cambiar los patrocinadores")
def patrocinadores(request: HttpRequest, pk: int) -> HttpResponse:
    torneo = get_object_or_404(Torneo, pk=pk)
    formulario = FormularioPatrocinador(
        request.POST or None, initial={"orden": torneo.patrocinadores.count() + 1}
    )
    error_imagen = ""
    if request.method == "POST" and formulario.is_valid():
        archivo = request.FILES.get("imagen")
        if archivo is None:
            error_imagen = "Elige la imagen del patrocinador."
        else:
            try:
                _agregar(torneo, formulario, archivo)
            except ImagenInvalida as error:
                error_imagen = str(error)
            else:
                messages.success(request, f"{formulario.cleaned_data['nombre']} agregado")
                return redirect("patrocinadores", pk=torneo.pk)
    lista = [
        {"modelo": p, "url": url_de_imagen("patrocinador", p.pk, p.imagen.name)}
        for p in torneo.patrocinadores.all()
    ]
    return render(
        request,
        "torneo/patrocinadores.html",
        {"torneo": torneo, "form": formulario, "lista": lista, "error_imagen": error_imagen},
    )


def _agregar(
    torneo: Torneo, formulario: FormularioPatrocinador, archivo: UploadedFile[bytes]
) -> None:
    if not settings.IMAGENES_DISPONIBLES:
        raise SinAlmacenamiento("Falta conectar el almacenamiento de imágenes.")
    imagen = procesar_imagen(archivo, tipo="patrocinador")
    Patrocinador.objects.create(
        torneo=torneo,
        nombre=formulario.cleaned_data["nombre"],
        orden=formulario.cleaned_data["orden"],
        imagen=imagen,
    )


@require_POST
@requiere("torneo.configurar_torneo", "cambiar los patrocinadores")
def orden(request: HttpRequest, pk: int) -> HttpResponse:
    patrocinador = get_object_or_404(Patrocinador, pk=pk)
    try:
        patrocinador.orden = max(0, min(99, int(request.POST.get("orden", ""))))
    except ValueError:
        messages.error(request, "El orden es un número.")
    else:
        patrocinador.save(update_fields=["orden"])
    return redirect("patrocinadores", pk=patrocinador.torneo_id)


@require_POST
@requiere("torneo.configurar_torneo", "cambiar los patrocinadores")
def borrar(request: HttpRequest, pk: int) -> HttpResponse:
    patrocinador = get_object_or_404(Patrocinador, pk=pk)
    torneo = patrocinador.torneo_id
    if not confirmado(request):
        return pedir_confirmacion(
            request,
            mensaje=f"Se quita {patrocinador.nombre} y se borra su imagen.",
            boton="Quitar",
            volver=reverse("patrocinadores", args=[torneo]),
            peligro=True,
        )
    patrocinador.imagen.delete(save=False)
    patrocinador.delete()
    messages.success(request, f"{patrocinador.nombre} quitado")
    return redirect("patrocinadores", pk=torneo)
