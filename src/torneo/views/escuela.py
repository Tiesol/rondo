"""Datos de la escuela: nombre y colores del organizador, sin admin (TU.7)."""

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from torneo.forms.escuela import FormularioEscuela
from torneo.models import Organizador
from torneo.permisos import requiere
from torneo.presentacion import url_de_imagen
from torneo.servicios.imagenes import ImagenInvalida, quitar_imagen, reemplazar_imagen


@requiere("torneo.configurar_torneo", "cambiar los datos de la escuela")
def escuela(request: HttpRequest) -> HttpResponse:
    organizador = Organizador.actual()
    formulario = FormularioEscuela(request.POST or None, instance=organizador)
    error_logo = ""
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        try:
            if request.POST.get("quitar_logo"):
                quitar_imagen(organizador.logo)
            elif archivo := request.FILES.get("logo"):
                reemplazar_imagen(organizador.logo, archivo, tipo="logo")  # T8.3
        except ImagenInvalida as error:
            error_logo = str(error)
        else:
            messages.success(request, "Datos de la escuela guardados")
            return redirect("escuela")
    logo = url_de_imagen("logo", organizador.pk, organizador.logo.name)
    return render(
        request, "torneo/escuela.html", {"form": formulario, "logo": logo, "error_logo": error_logo}
    )
