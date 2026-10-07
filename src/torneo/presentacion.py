"""Textos que se repiten en varias pantallas, armados en un solo lugar."""

from django.utils.formats import date_format

from torneo.models import CategoriaNivel, Torneo


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
