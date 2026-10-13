"""Rehacer el fixture con partidos jugados (T11.15, P44 y P80: los resultados cuentan).

Cuando cambia la cantidad de equipos de una categoría empezada, cambia el formato. Las series
nuevas se eligen para que sigan existiendo la mayor cantidad posible de partidos jugados: en
"series", los dos equipos en la misma serie; en "series_cruzadas", en series distintas; en
todos contra todos, siempre. Con empate, se separa a los equipos de un mismo club (P45). Lo
que no tiene lugar en el formato nuevo se descarta, y la pantalla lo muestra antes.
"""

from collections import Counter
from collections.abc import Callable, Hashable, Iterator, Sequence
from dataclasses import dataclass
from itertools import combinations
from string import ascii_uppercase

from dominio.formatos import Grupos

type Jugado[T] = tuple[Hashable, T, T]  # el partido y sus dos equipos


@dataclass(frozen=True)
class Plan[T]:
    series: dict[str, list[T]] | None  # None en todos contra todos
    conservados: tuple[Hashable, ...]
    descartados: tuple[Hashable, ...]


def _particiones[T](equipos: Sequence[T], tamanios: tuple[int, ...]) -> Iterator[list[list[T]]]:
    if len(tamanios) == 1:
        yield [list(equipos)]
        return
    for primera in combinations(equipos, tamanios[0]):
        resto = [e for e in equipos if e not in primera]
        for otras in _particiones(resto, tamanios[1:]):
            yield [list(primera), *otras]


def _repartir[T](
    jugados: Sequence[Jugado[T]],
    vale: Callable[[T, T], bool],
    equipos: set[T],
    veces: int,
) -> tuple[tuple[Hashable, ...], tuple[Hashable, ...]]:
    """Cada cruce existe `veces` veces en el formato nuevo (2 con ida y vuelta)."""
    usados: Counter[frozenset[T]] = Counter()
    conservados, descartados = [], []
    for partido, a, b in jugados:
        par = frozenset((a, b))
        if a in equipos and b in equipos and vale(a, b) and usados[par] < veces:
            usados[par] += 1
            conservados.append(partido)
        else:
            descartados.append(partido)
    return tuple(conservados), tuple(descartados)


def planear_rehacer[T: Hashable](
    grupos: Grupos,
    equipos: Sequence[T],
    jugados: Sequence[Jugado[T]],
    club_de: Callable[[T], Hashable],
) -> Plan[T]:
    veces = 2 if grupos.ida_y_vuelta else 1
    presentes = set(equipos)
    if not grupos.series:
        conservados, descartados = _repartir(jugados, lambda a, b: True, presentes, veces)
        return Plan(None, conservados, descartados)

    if len(grupos.series) == 2:
        particion = _dos_series(grupos, list(equipos), jugados, club_de, veces)
        serie_de = {e: i for i, lista in enumerate(particion) for e in lista}
        cruzadas = grupos.tipo == "series_cruzadas"
        conservados, descartados = _repartir(
            jugados, lambda a, b: (serie_de[a] != serie_de[b]) == cruzadas, presentes, veces
        )
        series = {ascii_uppercase[i]: lista for i, lista in enumerate(particion)}
        return Plan(series, conservados, descartados)

    mejor: tuple[tuple[int, int], list[list[T]], tuple[Hashable, ...], tuple[Hashable, ...]]
    mejor = ((-1, 0), [], (), ())
    for particion in _particiones(list(equipos), grupos.series):
        serie_de = {e: i for i, lista in enumerate(particion) for e in lista}

        def vale(a: T, b: T, serie_de: dict[T, int] = serie_de) -> bool:
            return (serie_de[a] != serie_de[b]) == (grupos.tipo == "series_cruzadas")

        conservados, descartados = _repartir(jugados, vale, presentes, veces)
        mismo_club = sum(
            1 for lista in particion for a, b in combinations(lista, 2) if club_de(a) == club_de(b)
        )
        puntaje = (len(conservados), -mismo_club)
        if puntaje > mejor[0]:
            mejor = (puntaje, particion, conservados, descartados)
    _, particion, conservados, descartados = mejor
    series = {ascii_uppercase[i]: lista for i, lista in enumerate(particion)}
    return Plan(series, conservados, descartados)


def _dos_series[T: Hashable](
    grupos: Grupos,
    equipos: list[T],
    jugados: Sequence[Jugado[T]],
    club_de: Callable[[T], Hashable],
    veces: int,
) -> list[list[T]]:
    """Lo mismo con dos series, rápido: cada reparto es una máscara de bits (la serie A), y
    con series del mismo tamaño el primer equipo va siempre en la A (la otra mitad es igual).
    Con 20 equipos son unas 90 000 máscaras."""
    indice = {e: i for i, e in enumerate(equipos)}
    pares: Counter[tuple[int, int]] = Counter()
    for _, a, b in jugados:
        if a in indice and b in indice and a != b:
            pares[tuple(sorted((indice[a], indice[b])))] += 1  # type: ignore[index]
    peso = [(i, j, min(n, veces)) for (i, j), n in pares.items()]
    clubes = [
        (i, j)
        for i, j in combinations(range(len(equipos)), 2)
        if club_de(equipos[i]) == club_de(equipos[j])
    ]
    cruzadas = grupos.tipo == "series_cruzadas"
    tam_a = grupos.series[0]
    simetrica = grupos.series[0] == grupos.series[1]
    resto = range(1, len(equipos)) if simetrica else range(len(equipos))
    mejor_puntaje, mejor_mascara = (-1, 0), 0
    for elegidos in combinations(resto, tam_a - 1 if simetrica else tam_a):
        mascara = 1 if simetrica else 0
        for i in elegidos:
            mascara |= 1 << i
        conservados = sum(
            w for i, j, w in peso if (((mascara >> i) ^ (mascara >> j)) & 1) == cruzadas
        )
        juntos = sum(1 for i, j in clubes if not ((mascara >> i) ^ (mascara >> j)) & 1)
        puntaje = (conservados, -juntos)
        if puntaje > mejor_puntaje:
            mejor_puntaje, mejor_mascara = puntaje, mascara
    serie_a = [e for i, e in enumerate(equipos) if mejor_mascara >> i & 1]
    serie_b = [e for i, e in enumerate(equipos) if not mejor_mascara >> i & 1]
    return [serie_a, serie_b]
