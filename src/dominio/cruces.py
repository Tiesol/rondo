"""Cruces de la fase de grupos (FIX-03 a FIX-05), con identificadores de equipo.

Se arman rondas (fechas) en las que nadie juega dos veces:

- todos contra todos, por el método del círculo (Berger), con un descanso si son impares;
- series cruzadas: cada equipo de una serie contra cada uno de la otra; si una es más
  grande, en cada fecha descansa uno de ella (con 4 y 3, uno de la A);
- dentro de cada serie: un todos contra todos por serie, con las fechas alineadas.

Después, la ronda con más cruces entre equipos del mismo club pasa a ser la fecha 1 (P24), y
con ida y vuelta se repiten las rondas con la localía invertida.
"""

from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass

from dominio.formatos import Grupos


@dataclass(frozen=True)
class Cruce[T]:
    fecha: int
    local: T
    visitante: T
    serie: str | None  # "A", "B", "A-B" en las cruzadas, None en todos contra todos


type _Ronda[T] = list[tuple[T, T, str | None]]


def _circulo[T](equipos: Sequence[T], serie: str | None) -> list[_Ronda[T]]:
    """Método del círculo: el primero queda fijo y los demás rotan."""
    lugares: list[T | None] = list(equipos)
    if len(lugares) % 2:
        lugares.append(None)  # descanso
    n = len(lugares)
    rondas: list[_Ronda[T]] = []
    for numero in range(n - 1):
        ronda: _Ronda[T] = []
        for i in range(n // 2):
            uno, otro = lugares[i], lugares[n - 1 - i]
            if uno is None or otro is None:
                continue
            # Alterna la localía del fijo, para que no sea siempre local.
            if i == 0 and numero % 2:
                uno, otro = otro, uno
            ronda.append((uno, otro, serie))
        rondas.append(ronda)
        lugares = [lugares[0], lugares[-1], *lugares[1:-1]]
    return rondas


def _cruzadas[T](una: Sequence[T], otra: Sequence[T]) -> list[_Ronda[T]]:
    """En la ronda r, el i de la serie grande juega con el (i + r) de la chica, si existe."""
    grande, chica = (una, otra) if len(una) >= len(otra) else (otra, una)
    rondas: list[_Ronda[T]] = []
    for r in range(len(grande)):
        ronda: _Ronda[T] = []
        for i, equipo in enumerate(grande):
            j = (i + r) % len(grande)
            if j < len(chica):
                local, visitante = (equipo, chica[j]) if (i + r) % 2 == 0 else (chica[j], equipo)
                ronda.append((local, visitante, "A-B"))
        rondas.append(ronda)
    return rondas


def _alinear[T](por_serie: list[list[_Ronda[T]]]) -> list[_Ronda[T]]:
    """Junta las rondas de cada serie: la fecha k tiene la ronda k de todas."""
    largo = max(len(rondas) for rondas in por_serie)
    return [
        [cruce for rondas in por_serie if k < len(rondas) for cruce in rondas[k]]
        for k in range(largo)
    ]


def _mismo_club_primero[T](
    rondas: list[_Ronda[T]], club_de: Callable[[T], Hashable]
) -> list[_Ronda[T]]:
    """P24: la ronda con más cruces entre equipos del mismo club va primero."""

    def del_mismo_club(ronda: _Ronda[T]) -> int:
        return sum(club_de(local) == club_de(visitante) for local, visitante, _ in ronda)

    mejor = max(range(len(rondas)), key=lambda k: del_mismo_club(rondas[k]), default=0)
    if not rondas or del_mismo_club(rondas[mejor]) == 0:
        return rondas
    return [rondas[mejor], *rondas[:mejor], *rondas[mejor + 1 :]]


def armar_grupos[T: Hashable](
    grupos: Grupos,
    series: dict[str, list[T]],
    club_de: Callable[[T], Hashable],
    *,
    mismo_club_fecha_1: bool,
) -> list[Cruce[T]]:
    """Los cruces de la fase de grupos, numerados por fecha desde 1.

    `series` trae los equipos de cada serie ("A", "B"…); en todos contra todos, una sola
    con cualquier nombre.
    """
    listas = list(series.values())
    if grupos.tipo == "todos_contra_todos":
        rondas = _circulo(listas[0], None)
    elif grupos.tipo == "series_cruzadas":
        rondas = _cruzadas(listas[0], listas[1])
    else:
        rondas = _alinear([_circulo(equipos, nombre) for nombre, equipos in series.items()])

    if mismo_club_fecha_1:
        rondas = _mismo_club_primero(rondas, club_de)
    if grupos.ida_y_vuelta:
        rondas = rondas + [[(vis, loc, serie) for loc, vis, serie in ronda] for ronda in rondas]

    return [
        Cruce(fecha, local, visitante, serie)
        for fecha, ronda in enumerate(rondas, start=1)
        for local, visitante, serie in ronda
    ]
