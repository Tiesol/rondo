"""Textos que se repiten en varias pantallas, armados en un solo lugar."""

from datetime import datetime

from django.utils import timezone
from django.utils.formats import date_format

from torneo.colores import texto_sobre
from torneo.models import CategoriaNivel, Equipo, Partido, Torneo


def fechas_del_torneo(torneo: Torneo) -> str:
    """ "Del viernes 23 de octubre al domingo 22 de noviembre · 5 fines de semana"."""
    formato = r"l j \d\e F"
    texto = f"Del {date_format(torneo.inicio, formato)} al {date_format(torneo.fin, formato)}"
    semanas = torneo.fines_de_semana
    if semanas:
        texto += f" · {semanas} {'fin de semana' if semanas == 1 else 'fines de semana'}"
    return texto


def edicion(torneo: Torneo) -> str:
    return f"{torneo.edicion}.ª edición"


def nacidos_en(categoria: CategoriaNivel) -> str:
    primero = categoria.torneo.anio - categoria.edad
    return " o ".join(str(primero + i) for i in range(categoria.anios_nacimiento))


def resumen_de_categoria(categoria: CategoriaNivel) -> str:
    """ "F7 · 12 a 14 jugadores · turno de 50 min · nacidos en 2017"."""
    return (
        f"{categoria.modalidad} · {categoria.min_jugadores} a {categoria.max_jugadores} "
        f"jugadores · turno de {categoria.minutos_turno} min · nacidos en {nacidos_en(categoria)}"
    )


def sigla_de_equipo(nombre: str) -> str:
    """ "River Plate" da "RIV"; "De Taquito", "DT": la primera palabra si es larga."""
    palabras = nombre.split()
    if not palabras:
        return ""
    if len(palabras[0]) >= 3:
        return palabras[0][:3].upper()
    return "".join(p[0] for p in palabras[:3]).upper()


def escudo(equipo: Equipo) -> dict[str, str]:
    """Lo que necesita parciales/escudo.html: sigla y colores (o los del tema)."""
    return {
        "sigla": sigla_de_equipo(equipo.nombre),
        "color": equipo.color_1,
        "texto": texto_sobre(equipo.color_1) if equipo.color_1 else "",
    }


DIAS_CORTOS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def lugar(inicio: datetime | None, cancha: str = "") -> str:
    """ "Sáb 24 · 10:10 · C1", en hora de Bolivia. Vacío si no está programado."""
    if inicio is None:
        return "Sin programar"
    local = timezone.localtime(inicio)
    texto = f"{DIAS_CORTOS[local.weekday()]} {local.day} · {local:%H:%M}"
    return f"{texto} · {cancha}" if cancha else texto


def cruce(partido: Partido) -> str:
    """ "River Plate vs Planeta FC", o las referencias si está por definir."""
    local = partido.local.nombre if partido.local else partido.texto_local
    visitante = partido.visitante.nombre if partido.visitante else partido.texto_visitante
    return f"{local} vs {visitante}"
