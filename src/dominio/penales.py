"""Penales tiro por tiro (T11.13, P83): `por_equipo` por lado (3 en la plantilla) y, si
siguen empatados, uno más por equipo hasta que se defina (muerte súbita). La tanda se corta
apenas un equipo ya no puede alcanzar al otro."""

from dataclasses import dataclass

from dominio.partido import Lado

Tiro = tuple[Lado, bool]  # quién pateó y si convirtió


@dataclass(frozen=True)
class EstadoDePenales:
    local: int
    visitante: int
    ganador: Lado | None
    muerte_subita: bool
    patea: Lado | None  # a quién le toca; None si es el primero o ya hay ganador


def estado_de_penales(tiros: list[Tiro], *, por_equipo: int) -> EstadoDePenales:
    goles = {"local": 0, "visitante": 0}
    pateados = {"local": 0, "visitante": 0}
    for lado, convirtio in tiros:
        pateados[lado] += 1
        goles[lado] += int(convirtio)
    local, visitante = goles["local"], goles["visitante"]
    muerte_subita = min(pateados.values()) >= por_equipo
    ganador: Lado | None = None
    if not muerte_subita:
        quedan_local = max(por_equipo - pateados["local"], 0)
        quedan_visitante = max(por_equipo - pateados["visitante"], 0)
        if local > visitante + quedan_visitante:
            ganador = "local"
        elif visitante > local + quedan_local:
            ganador = "visitante"
    elif pateados["local"] == pateados["visitante"] and local != visitante:
        ganador = "local" if local > visitante else "visitante"

    patea: Lado | None = None
    if ganador is None and tiros:
        if pateados["local"] != pateados["visitante"]:
            patea = "local" if pateados["local"] < pateados["visitante"] else "visitante"
        else:
            patea = tiros[0][0]  # empieza la ronda el que empezó la tanda
    return EstadoDePenales(local, visitante, ganador, muerte_subita, patea)
