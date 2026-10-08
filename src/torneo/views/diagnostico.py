"""Páginas de diagnóstico, solo para staff: el muestrario de los componentes (TU.1)."""

from django import forms
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

# TU.1: muestrario de los parciales de la interfaz, con datos inventados.
PENDIENTES_DE_MUESTRA = [
    {
        "titulo": "3 equipos debajo del mínimo de jugadores",
        "sub": "Sub 8 Avanzado, Sub 12 Inicial y Sub 17 Avanzado",
        "url": "#",
        "icono": "personas",
        "estado": "aviso",
    },
    {
        "titulo": "41 jugadores sin verificar el CI",
        "sub": "La mesa los marca al ver el documento original",
        "url": "#",
        "icono": "documento",
        "estado": "info",
    },
    {
        "titulo": "La eliminación no entra en el último fin de semana",
        "sub": "Faltan 15 horas en C1 y C2",
        "url": "#",
        "icono": "aviso",
        "estado": "error",
    },
]
FILAS_DE_MUESTRA = [
    {
        "titulo": "River Plate",
        "sub": "13 de 14 jugadores",
        "chip": "Completo",
        "chip_estado": "bien",
    },
    {
        "titulo": "Planeta FC",
        "sub": "9 de 14 jugadores",
        "chip": "Faltan 3",
        "chip_estado": "aviso",
    },
    {"titulo": "Leones", "sub": "Sin lista", "chip": "Choque con un profe", "chip_estado": "error"},
]


class FormularioDeMuestra(forms.Form):
    nombre = forms.CharField(help_text="Aparece en la banda y en la página pública.")
    edicion = forms.IntegerField(label="Edición", min_value=1)


def componentes(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        raise PermissionDenied
    pestana = request.GET.get("pestana", "equipos")
    pestanas = [
        {"url": f"?pestana={clave}", "texto": texto, "actual": clave == pestana}
        for clave, texto in [
            ("equipos", "Equipos"),
            ("fixture", "Fixture"),
            ("posiciones", "Posiciones"),
            ("ajustes", "Ajustes"),
        ]
    ]
    return render(
        request,
        "diagnostico/componentes.html",
        {
            "pendientes": PENDIENTES_DE_MUESTRA,
            "filas": FILAS_DE_MUESTRA,
            "pestanas": pestanas,
            "form": FormularioDeMuestra({"nombre": "JMP CUP 2026", "edicion": "0"}),
            "escudo_muestra": {"sigla": "RIV", "color": "", "texto": ""},
        },
    )
