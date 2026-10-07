"""Páginas de prueba de riesgo de la fase 0. Solo para staff; se borran al cerrar la fase 4."""

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
