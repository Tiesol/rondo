"""Personas y roles desde la app (T6.2), sin terminal."""

from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_POST

from torneo.forms.personas import FormularioPersona, FormularioRol
from torneo.permisos import requiere
from torneo.servicios.usuarios import cambiar_rol, crear_usuario


@sensitive_post_parameters()
@sensitive_variables("clave")
@requiere("torneo.configurar_torneo", "agregar personas")
def nueva(request: HttpRequest) -> HttpResponse:
    formulario = FormularioPersona(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        datos = formulario.cleaned_data
        usuario, clave = crear_usuario(datos["usuario"], datos["nombre"], datos["rol"])
        # Se muestra una sola vez, en esta respuesta; no queda en mensajes ni en la sesión.
        respuesta = render(request, "personas/creada.html", {"nuevo": usuario, "clave": clave})
        respuesta["Cache-Control"] = "no-store"
        return respuesta
    return render(request, "personas/nueva.html", {"form": formulario})


@require_POST
@requiere("torneo.configurar_torneo", "cambiar roles")
def rol(request: HttpRequest, pk: int) -> HttpResponse:
    persona = get_object_or_404(User, pk=pk)
    formulario = FormularioRol(request.POST)
    if persona.pk == request.user.pk:
        messages.error(
            request, "No puedes cambiar tu propio rol: pídeselo a otra persona de la organización."
        )
    elif persona.is_superuser:
        messages.error(request, "El rol del administrador no se cambia desde acá.")
    elif formulario.is_valid():
        cambiar_rol(persona, formulario.cleaned_data["rol"])
        messages.success(request, f"Rol de {persona.username} cambiado")
    return redirect("mas")
