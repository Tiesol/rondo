"""Páginas de diagnóstico, solo para staff. Las de la fase 0 se borran al cerrar la fase 4."""

from django import forms
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

# Sábado 14 de octubre de 2023 (sección 6.3), solo con equipos, canchas y horarios.
PARTIDOS_DE_PRUEBA = {
    "C1": [
        ("09:20", "Sub 11 Av A", "River Plate", "Super Campeones"),
        ("10:10", "Sub 11 Av B", "Planeta FC", "Oriente Petrolero"),
        ("11:00", "Sub 11 Av B", "Blooming", "Torito García"),
        ("11:50", "Sub 9 Ini", "Torito García", "Real FC"),
    ],
    "C1A": [
        ("08:00", "Sub 5", "JMP Soccer", "Leones"),
        ("08:40", "Sub 6 B", "JMP Academy", "Maravillita"),
    ],
    "C1B": [
        ("08:00", "Sub 6 A", "JMP Soccer", "Panteras FC"),
        ("08:40", "Sub 6 B", "Super Campeones", "Planeta FC"),
    ],
    "C2": [
        ("08:00", "Sub 8 Ini", "Leoncitos", "Real FC"),
        ("08:50", "Sub 10 Ini", "Inter Star", "Leones PFC"),
        ("09:40", "Sub 10 Av", "JMP Soccer", "Leones"),
        ("10:30", "Sub 10 Av", "Planeta FC", "Libertad"),
        ("11:20", "Sub 11 Ini", "JMP Soccer", "Inter Star"),
        ("12:10", "Sub 11 Ini", "Real FC", "Petrolero"),
    ],
    "C3": [
        ("08:00", "Sub 12 A", "Oriente Petrolero", "Planeta FC"),
        ("09:00", "Sub 12 B", "Atlético Juniors", "Crack FC"),
        ("10:00", "Sub 15", "JMP Academy", "River Plate"),
        ("11:10", "Sub 13 B", "Inter Star", "Atlético Juniors"),
    ],
}


def png(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        raise PermissionDenied
    return render(request, "diagnostico/png.html", {"canchas": PARTIDOS_DE_PRUEBA})


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
        },
    )
