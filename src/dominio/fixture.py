"""El fixture de una categoría: sorteo de series y todos sus partidos (FIX-06, FIX-08).

Trabaja con identificadores de equipo. El servicio guarda el resultado en la base.
"""

import random
from collections import Counter
from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass, field
from string import ascii_uppercase
from typing import Literal

from dominio.cruces import armar_grupos
from dominio.formatos import Copa, FormatoParaN, Ronda


class SeriesInvalidas(ValueError):
    """Las series elegidas a mano no tienen los tamaños del formato."""


@dataclass(frozen=True)
class PartidoDelFixture[T]:
    fase: Literal["grupos", "eliminacion"]
    local: T | None
    visitante: T | None
    fecha: int | None = None  # en la fase de grupos
    serie: str | None = None
    clave: str = ""  # en la eliminación: "oro_semi_1"
    nombre: str = ""
    copa: Copa | None = None
    ronda: Ronda | None = None
    texto_local: str = ""  # "1.º A" mientras el participante esté por definir
    texto_visitante: str = ""


@dataclass(frozen=True)
class Fixture[T]:
    series: dict[str, list[T]]  # vacío en todos contra todos
    partidos: list[PartidoDelFixture[T]] = field(default_factory=list)


def sortear_series[T: Hashable](
    equipos: Sequence[T],
    tamanios: tuple[int, ...],
    club_de: Callable[[T], Hashable],
    *,
    semilla: int,
    separar_clubes: bool,
) -> dict[str, list[T]]:
    """P45: sorteo con semilla. Si se separan clubes, los de un mismo club van a series
    distintas mientras haya lugar; los clubes con más equipos se reparten primero."""
    azar = random.Random(semilla)
    mezclados = list(equipos)
    azar.shuffle(mezclados)
    nombres = ascii_uppercase[: len(tamanios)]
    series: dict[str, list[T]] = {nombre: [] for nombre in nombres}
    lugares = dict(zip(nombres, tamanios, strict=True))

    if separar_clubes:
        cuantos = Counter(club_de(e) for e in mezclados)
        orden = sorted(mezclados, key=lambda e: -cuantos[club_de(e)])  # sorted es estable
    else:
        orden = mezclados
    for equipo in orden:
        club = club_de(equipo)
        libres = [n for n in nombres if len(series[n]) < lugares[n]]
        destino = min(
            libres,
            key=lambda n: (
                sum(club_de(e) == club for e in series[n]) if separar_clubes else 0,
                -(lugares[n] - len(series[n])),
                n,
            ),
        )
        series[destino].append(equipo)
    return series


def armar_fixture[T: Hashable](
    formato: FormatoParaN,
    equipos: Sequence[T],
    club_de: Callable[[T], Hashable],
    *,
    semilla: int,
    separar_clubes: bool,
    mismo_club_fecha_1: bool,
    series: dict[str, list[T]] | None = None,
) -> Fixture[T]:
    """Grupos con sus fechas y eliminación con participantes por definir (FIX-08)."""
    grupos = formato.grupos
    if grupos.series:
        if series is None:
            series = sortear_series(
                equipos, grupos.series, club_de, semilla=semilla, separar_clubes=separar_clubes
            )
        tamanios = tuple(len(s) for s in series.values())
        if tamanios != grupos.series:
            esperado = " y ".join(str(t) for t in grupos.series)
            raise SeriesInvalidas(
                f"Con {formato.equipos} equipos, las series son de {esperado}; "
                f"ahora son de {' y '.join(str(t) for t in tamanios)}."
            )
        de_grupos = series
    else:
        series = {}
        de_grupos = {"": list(equipos)}

    partidos: list[PartidoDelFixture[T]] = [
        PartidoDelFixture("grupos", c.local, c.visitante, fecha=c.fecha, serie=c.serie)
        for c in armar_grupos(grupos, de_grupos, club_de, mismo_club_fecha_1=mismo_club_fecha_1)
    ]
    partidos += [
        PartidoDelFixture(
            "eliminacion",
            None,
            None,
            clave=llave.clave,
            nombre=llave.nombre,
            copa=llave.copa,
            ronda=llave.ronda,
            texto_local=llave.local.texto,
            texto_visitante=llave.visitante.texto,
        )
        for llave in formato.eliminacion
    ]
    return Fixture(series, partidos)
