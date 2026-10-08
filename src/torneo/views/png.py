"""PNG del día por cancha (T5.6; criterio 6): solo equipos, canchas y horarios.

Nunca carga personas: lo controla tests/torneo/test_png.py.
"""

from datetime import date, datetime, time, timedelta
from typing import Any

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from torneo.models import Cancha, Partido, Torneo
from torneo.presentacion import escudo

FILAS_POR_IMAGEN = 5  # lo que entra en la pieza de 1220 por 690 sin achicar las filas
DIAS = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]


def _corta(categoria: str) -> str:
    return categoria.replace("Avanzado", "Av").replace("Inicial", "Ini").replace("Femenino", "Fem")


def _lado(equipo: Any, texto: str) -> dict[str, Any]:
    if equipo is None:
        return {"nombre": texto, "escudo": None}
    return {"nombre": equipo.nombre, "escudo": escudo(equipo)}


def png(request: HttpRequest, fecha: str) -> HttpResponse:
    torneo = Torneo.activo()
    if torneo is None:
        return redirect("inicio")
    try:
        dia = date.fromisoformat(fecha)
    except ValueError:
        raise Http404 from None
    desde = timezone.make_aware(datetime.combine(dia, time.min))
    partidos = (
        Partido.objects.filter(
            categoria__torneo=torneo, inicio__gte=desde, inicio__lt=desde + timedelta(days=1)
        )
        .select_related("cancha__padre", "local", "visitante", "categoria")
        .order_by("inicio", "cancha__codigo")
    )
    por_cancha: dict[str, list[dict[str, Any]]] = {}
    for partido in partidos:
        if partido.cancha is None or partido.inicio is None:
            continue
        entera = partido.cancha.padre or partido.cancha
        por_cancha.setdefault(entera.codigo, []).append(
            {
                "categoria": _corta(str(partido.categoria)),
                "mitad": partido.cancha.codigo if partido.cancha.padre else "",
                "local": _lado(partido.local, partido.texto_local),
                "visitante": _lado(partido.visitante, partido.texto_visitante),
                "hora": timezone.localtime(partido.inicio).strftime("%H:%M"),
            }
        )

    piezas = []
    for cancha in Cancha.objects.filter(torneo=torneo, padre__isnull=True).order_by("codigo"):
        filas = por_cancha.get(cancha.codigo, [])
        tandas = [filas[i : i + FILAS_POR_IMAGEN] for i in range(0, len(filas), FILAS_POR_IMAGEN)]
        for numero, tanda in enumerate(tandas, start=1):
            piezas.append(
                {
                    "id": f"pieza-{cancha.codigo}-{numero}",
                    "cancha": cancha.nombre.upper(),
                    "pagina": f"{numero}/{len(tandas)}" if len(tandas) > 1 else "",
                    "filas": tanda,
                    "vacias": range(FILAS_POR_IMAGEN - len(tanda)),
                    "archivo": f"fixture-{dia.isoformat()}-{cancha.codigo}-{numero}.png",
                }
            )
    return render(
        request,
        "calendario/png.html",
        {
            "torneo": torneo,
            "dia": dia,
            "titulo_dia": f"{DIAS[dia.weekday()]} {dia.day}",
            "marca": torneo.nombre_sin_anio.upper(),
            "edicion": f"{torneo.edicion}.ª edición",
            "piezas": piezas,
        },
    )
