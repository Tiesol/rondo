"""Asistente para crear un torneo desde la plantilla del reglamento (TU.4).

Lo cargado se guarda en la sesión paso a paso. Al terminar se arma la configuración, se valida
con el dominio y se carga con el mismo servicio que usa `manage.py cargar_config`.
"""

from typing import Any

from django import forms
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from pydantic import ValidationError

from torneo.forms.asistente import FormularioDatos, FormularioFranjas, FormularioNiveles
from torneo.forms.reglas import FormularioReglas
from torneo.models import Torneo
from torneo.permisos import requiere
from torneo.servicios.asistente import Respuestas, armar, niveles_de, plantilla
from torneo.servicios.configuracion import cargar_configuracion

SESION = "asistente"
PASOS = ("Datos", "Categorías", "Canchas y horarios", "Reglas")


def _formulario(paso: int, datos: Any, respuestas: Respuestas) -> forms.Form:
    base = plantilla()
    if paso == 1:
        torneo = base["torneo"]
        inicial = respuestas.get("datos") or {
            clave: torneo[clave] for clave in ("nombre", "edicion", "inicio", "fin")
        }
        return FormularioDatos(datos, initial=inicial)
    if paso == 2:
        niveles = niveles_de(armar(base, {"datos": respuestas["datos"]}).model_dump(mode="json"))
        elegidos = respuestas.get("niveles", [n["clave"] for n in niveles])
        return FormularioNiveles(datos, niveles=niveles, initial={"niveles": elegidos})
    if paso == 3:
        franjas = respuestas.get("franjas", base["franjas"])
        return FormularioFranjas(datos, initial=FormularioFranjas.iniciales(franjas))
    return FormularioReglas(datos, initial=respuestas.get("reglas", base["reglas"]))


def _respuesta(paso: int, formulario: forms.Form) -> Any:
    if isinstance(formulario, (FormularioDatos, FormularioFranjas)):
        return formulario.respuesta()
    if isinstance(formulario, FormularioNiveles):
        return formulario.cleaned_data["niveles"]
    assert isinstance(formulario, FormularioReglas)
    return formulario.reglas.model_dump(mode="json")


CLAVES = {1: "datos", 2: "niveles", 3: "franjas", 4: "reglas"}


@requiere("torneo.configurar_torneo", "crear torneos")
def empezar(request: HttpRequest) -> HttpResponse:
    request.session.pop(SESION, None)
    return redirect("asistente", paso=1)


@requiere("torneo.configurar_torneo", "crear torneos")
def asistente(request: HttpRequest, paso: int) -> HttpResponse:
    estado: dict[str, Any] = request.session.get(SESION, {"respuestas": {}, "hecho": 0})
    if not 1 <= paso <= len(PASOS) or paso > estado["hecho"] + 1:
        return redirect("asistente", paso=estado["hecho"] + 1)
    respuestas: Respuestas = estado["respuestas"]

    formulario = _formulario(paso, request.POST or None, respuestas)
    if request.method == "POST":
        atras = request.POST.get("ir") == "atras"
        if formulario.is_valid():
            respuestas[CLAVES[paso]] = _respuesta(paso, formulario)
            estado["hecho"] = max(estado["hecho"], paso)
            request.session[SESION] = estado
            if paso == len(PASOS) and not atras:
                return _crear(request, formulario, respuestas)
        if atras:
            return redirect("asistente", paso=max(paso - 1, 1))
        if formulario.is_valid():
            return redirect("asistente", paso=paso + 1)

    return render(
        request,
        "torneo/asistente.html",
        {
            "form": formulario,
            "paso": paso,
            "pasos": [
                {"numero": n, "nombre": nombre, "hecho": n < paso, "actual": n == paso}
                for n, nombre in enumerate(PASOS, start=1)
            ],
            "ultimo": paso == len(PASOS),
            "datos": respuestas.get("datos", {}),
        },
    )


def _crear(request: HttpRequest, formulario: forms.Form, respuestas: Respuestas) -> HttpResponse:
    try:
        config = armar(plantilla(), respuestas)
    except ValidationError as error:
        for detalle in error.errors():
            lugar = ".".join(str(p) for p in detalle["loc"])
            formulario.add_error(None, f"{lugar}: {detalle['msg']}")
        return render(
            request,
            "torneo/asistente.html",
            {"form": formulario, "paso": len(PASOS), "pasos": [], "ultimo": True},
        )
    if Torneo.objects.filter(nombre=config.torneo.nombre, anio=config.torneo.anio).exists():
        # Lo crearon mientras tanto (otra pestaña o la terminal): nunca se pisa.
        formulario.add_error(
            None,
            f"Ya existe un torneo «{config.torneo.nombre}» en {config.torneo.anio}. "
            "Vuelve al paso 1 y usa otro nombre.",
        )
        return render(
            request,
            "torneo/asistente.html",
            {"form": formulario, "paso": len(PASOS), "pasos": [], "ultimo": True},
        )
    torneo = cargar_configuracion(config)
    del request.session[SESION]
    messages.success(request, f"Torneo «{torneo.nombre}» creado")
    return redirect("inicio")
