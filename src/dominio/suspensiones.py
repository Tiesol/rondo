"""Suspensiones (T8.9; B5, CONTEXTO 4.7, P29 y P74).

- Doble amarilla desde la edad de la regla (Sub 10 a Sub 17): es roja; si no se pagó la multa,
  el jugador queda suspendido el próximo partido de su equipo. Más abajo de esa edad, dos
  amarillas sacan al jugador unos minutos y nada más.
- Roja directa y amarillas acumuladas: suspenden solo si la regla lo dice. Por defecto no
  (P29): lo decide la organización en cada caso, con una suspensión a mano.

Un incidente en un partido suspende los N partidos siguientes de su equipo.
"""

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

# Identificadores: los de la base, o textos en los tests.
Jugador = Any
Partido = Any
Equipo = Any
Tarjeta = tuple[Jugador, Partido, str]  # tipo: "amarilla" o "roja"


@dataclass(frozen=True)
class Incidente:
    jugador: Jugador
    equipo: Equipo
    partido: Partido  # donde pasó
    partidos: int  # cuántos partidos siguientes no juega
    motivo: str


@dataclass(frozen=True)
class Suspension:
    jugador: Jugador
    partido: Partido  # el que no puede jugar
    motivo: str


def suspendidos(
    incidentes: Iterable[Incidente], orden: Mapping[Equipo, Sequence[Partido]]
) -> list[Suspension]:
    """Los partidos que cada jugador no puede jugar. `orden`: los partidos de cada equipo, en
    el orden en que se juegan."""
    resultado = []
    for incidente in incidentes:
        partidos = list(orden.get(incidente.equipo, []))
        if incidente.partido not in partidos:
            continue
        siguientes = partidos[partidos.index(incidente.partido) + 1 :][: incidente.partidos]
        resultado += [Suspension(incidente.jugador, p, incidente.motivo) for p in siguientes]
    return resultado


def incidentes_de_tarjetas(
    tarjetas: Iterable[Tarjeta],
    *,
    equipo_de: Mapping[Jugador, Equipo],
    edad: int,
    orden: Mapping[Equipo, Sequence[Partido]],
    pagadas: set[tuple[Jugador, Partido]] | None = None,
    doble_amarilla_desde: int = 10,
    partidos_por_roja: int = 0,
    amarillas_acumuladas: int = 0,
) -> list[Incidente]:
    pagadas = pagadas or set()
    lista = list(tarjetas)
    amarillas = Counter((j, p) for j, p, tipo in lista if tipo == "amarilla")
    incidentes = []
    dobles = {clave for clave, n in amarillas.items() if n >= 2}
    if edad >= doble_amarilla_desde:
        for jugador, partido in sorted(dobles - pagadas, key=str):
            incidentes.append(
                Incidente(
                    jugador, equipo_de[jugador], partido, 1, "Doble amarilla sin pagar la multa"
                )
            )
    if partidos_por_roja:
        for jugador, partido, tipo in lista:
            if tipo == "roja" and (jugador, partido) not in dobles:
                incidentes.append(
                    Incidente(
                        jugador, equipo_de[jugador], partido, partidos_por_roja, "Roja directa"
                    )
                )
    if amarillas_acumuladas:
        for jugador in {j for j, _ in amarillas}:
            partidos = orden.get(equipo_de[jugador], [])
            cuenta = 0
            for partido in partidos:
                n = amarillas.get((jugador, partido), 0)
                if (jugador, partido) in dobles:
                    continue  # esa ya se castiga como doble amarilla
                cuenta += n
                if n and cuenta % amarillas_acumuladas == 0:
                    incidentes.append(
                        Incidente(
                            jugador,
                            equipo_de[jugador],
                            partido,
                            1,
                            f"{amarillas_acumuladas} amarillas acumuladas",
                        )
                    )
    return incidentes
