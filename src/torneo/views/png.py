"""PNG del día por cancha con el diseño 2026 (T8.12; docs/disenio_fixture/DISENO_FIXTURE_2026.md).

Una imagen de 1920 x 1080 por cancha y por día: el fondo trae todo lo fijo (mármol, copa,
"PROGRAMACIÓN", franja azul y logo); la app dibuja encima el título, las filas y los
patrocinadores. Si no entran, la cancha se parte en "1/2", "2/2". Nunca carga personas: lo
controla tests/torneo/test_png.py.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from torneo.models import Cancha, Partido, Torneo
from torneo.presentacion import escudo
from torneo.servicios.publico import patrocinadores_de

DIAS = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]
# Medidas del diseño en la pieza de 1920 x 1080 (las del PSD divididas por 2).
PRIMERA_FILA = 209.5  # el borde de arriba de la primera fila
ENTRE_FILAS = 60  # de una fila a la siguiente (la fila mide 61: se tocan)
ALTO_FILA = 61
ENTRE_BLOQUES = 50  # el espacio entre dos categorías
LIMITE = 900  # la franja azul empieza en 911,5: las filas terminan antes
INICIAL = {"avanzado": "A", "inicial": "I"}
# Nombres largos: se achica la letra hasta un mínimo (el JS de la página lo afina con la
# medida real). En Cinzel, una mayúscula ocupa en promedio unos 0,65 em.
ANCHO_LETRA = 0.65


def tamano(texto: str, ancho: float, normal: float, minimo: float) -> float:
    """El tamaño de letra para que `texto` entre en `ancho` px, sin bajar del mínimo."""
    if not texto:
        return normal
    return round(max(minimo, min(normal, ancho / (len(texto) * ANCHO_LETRA))), 1)


@dataclass
class _Pieza:
    filas: list[dict[str, Any]] = field(default_factory=list)
    y: float = PRIMERA_FILA


def _etiqueta(partido: Partido, niveles_juntos: set[str]) -> str:
    """ "SUB 7". Con Inicial y Avanzado de la misma categoría en la cancha, "SUB 7 A" o
    "SUB 7 I"; en media cancha, con la mitad ("SUB 5 · C1A")."""
    texto = partido.categoria.categoria.upper()
    if partido.categoria.categoria in niveles_juntos:
        texto += f" {INICIAL.get(partido.categoria.nivel, '')}".rstrip()
    if partido.cancha is not None and partido.cancha.padre is not None:
        texto += f" · {partido.cancha.codigo}"
    return texto


def _lado(equipo: Any, texto: str) -> tuple[str, str]:
    """(nombre, URL del escudo si el club lo tiene; la sigla no va en el PNG)."""
    if equipo is None:
        return texto, ""
    return equipo.nombre, escudo(equipo)["url"]


def paginar(partidos: list[Partido]) -> list[list[dict[str, Any]]]:
    """Las filas de una cancha, repartidas en piezas: bloques por categoría, cada bloque empieza
    en dorado y alterna, y ninguna fila pasa del límite."""
    niveles: dict[str, set[str]] = defaultdict(set)
    for p in partidos:
        niveles[p.categoria.categoria].add(p.categoria.nivel)
    juntos = {c for c, n in niveles.items() if len(n) > 1}
    piezas = [_Pieza()]
    anterior = ""
    alterna = 0
    for p in partidos:
        etiqueta = _etiqueta(p, juntos)
        pieza = piezas[-1]
        nuevo_bloque = etiqueta != anterior
        y = pieza.y + (ENTRE_BLOQUES if nuevo_bloque and pieza.filas else 0)
        if y + ALTO_FILA > LIMITE:
            pieza = _Pieza()
            piezas.append(pieza)
            y = pieza.y
        alterna = 0 if nuevo_bloque else alterna + 1
        local, escudo_local = _lado(p.local, p.texto_local)
        visitante, escudo_visitante = _lado(p.visitante, p.texto_visitante)
        pieza.filas.append(
            {
                "y": y,
                "color": "oro" if alterna % 2 == 0 else "blanca",
                "categoria": etiqueta,
                "tam_categoria": tamano(etiqueta, 88, 25.5, 16),
                "tam_local": tamano(local, 359 if escudo_local else 409, 30, 23),
                "tam_visitante": tamano(visitante, 388 if escudo_visitante else 438, 30, 23),
                "hora": timezone.localtime(p.inicio).strftime("%H:%M") if p.inicio else "",
                "local": local,
                "visitante": visitante,
                "escudo_local": escudo_local,
                "escudo_visitante": escudo_visitante,
            }
        )
        pieza.y = y + ENTRE_FILAS
        anterior = etiqueta
    return [p.filas for p in piezas if p.filas]


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
    por_cancha: dict[str, list[Partido]] = defaultdict(list)
    for partido in partidos:
        if partido.cancha is not None and partido.inicio is not None:
            por_cancha[(partido.cancha.padre or partido.cancha).codigo].append(partido)

    titulo_dia = f"{DIAS[dia.weekday()]} {dia.day}"
    piezas = []
    for cancha in Cancha.objects.filter(torneo=torneo, padre__isnull=True).order_by("codigo"):
        paginas = paginar(por_cancha.get(cancha.codigo, []))
        for numero, filas in enumerate(paginas, start=1):
            pagina = f" {numero}/{len(paginas)}" if len(paginas) > 1 else ""
            piezas.append(
                {
                    "id": f"pieza-{cancha.codigo}-{numero}",
                    "cancha": cancha.nombre,
                    "titulo": f"{cancha.nombre.upper()} ~ {titulo_dia}{pagina}",
                    "pagina": pagina.strip(),
                    "filas": filas,
                    "archivo": f"fixture-{dia.isoformat()}-{cancha.codigo}-{numero}.png",
                }
            )
    return render(
        request,
        "calendario/png.html",
        {
            "torneo": torneo,
            "dia": dia,
            "titulo_dia": titulo_dia.capitalize(),
            "piezas": piezas,
            "patrocinadores": patrocinadores_de(torneo),
            "borrador": not torneo.publico,
        },
    )
