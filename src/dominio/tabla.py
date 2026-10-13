"""Tabla de posiciones de un grupo (T8.7; CONTEXTO 4.6, P26, P28 y P34).

Orden del reglamento 2025: más puntos y, entre los empatados, considerando solo los partidos
entre ellos: puntos, goles a favor, menos goles en contra y fair play (menos tarjetas). Si los
empatados no jugaron todos entre sí (series cruzadas, H5), se usan todos los partidos del
grupo (P34). Si siguen empatados, el sorteo que registra la organización (P28).

El criterio "diferencia_de_gol" es el del Excel de 2023 (diferencia de gol y después goles a
favor, con todos los partidos): queda como opción porque así se hizo antes.

Supuesto: el fair play cuenta amarillas y rojas por igual, y usa las de todo el grupo.
"""

from collections.abc import Callable, Hashable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from fractions import Fraction
from itertools import combinations
from typing import Literal

Equipo = Hashable
Criterio = Literal["reglamento_2025", "diferencia_de_gol"]
_Desempate = Callable[[list[Equipo]], list[tuple[Equipo, bool]]]


@dataclass(frozen=True)
class Jugado:
    local: Equipo
    visitante: Equipo
    goles_local: int
    goles_visitante: int


@dataclass(frozen=True)
class Tarjetas:
    amarillas: int = 0
    rojas: int = 0

    @property
    def total(self) -> int:
        return self.amarillas + self.rojas


@dataclass(frozen=True)
class Fila:
    equipo: Equipo
    pj: int = 0
    pg: int = 0
    pe: int = 0
    pp: int = 0
    gf: int = 0
    gc: int = 0
    puntos: int = 0
    tarjetas: Tarjetas = field(default_factory=Tarjetas)
    posicion: int = 0
    falta_sorteo: bool = False

    @property
    def dg(self) -> int:
        return self.gf - self.gc


def _filas(
    equipos: Sequence[Equipo], partidos: Sequence[Jugado], puntos: tuple[int, int]
) -> dict[Equipo, Fila]:
    por_ganar, por_empatar = puntos
    filas = {e: Fila(e) for e in equipos}
    for p in partidos:
        for equipo, a_favor, en_contra in (
            (p.local, p.goles_local, p.goles_visitante),
            (p.visitante, p.goles_visitante, p.goles_local),
        ):
            if equipo not in filas:
                continue
            f = filas[equipo]
            gano, empato = a_favor > en_contra, a_favor == en_contra
            filas[equipo] = replace(
                f,
                pj=f.pj + 1,
                pg=f.pg + gano,
                pe=f.pe + empato,
                pp=f.pp + (not gano and not empato),
                gf=f.gf + a_favor,
                gc=f.gc + en_contra,
                puntos=f.puntos + (por_ganar if gano else por_empatar if empato else 0),
            )
    return filas


def _jugaron_todos(grupo: set[Equipo], partidos: Sequence[Jugado]) -> bool:
    jugados = {frozenset((p.local, p.visitante)) for p in partidos}
    return all(frozenset(par) in jugados for par in combinations(grupo, 2))


def tabla(
    equipos: Sequence[Equipo],
    partidos: Sequence[Jugado],
    *,
    puntos: tuple[int, int] = (3, 1),
    tarjetas: Mapping[Equipo, Tarjetas] | None = None,
    sorteo: Mapping[Equipo, int] | None = None,
    criterio: Criterio = "reglamento_2025",
) -> list[Fila]:
    """La tabla del grupo, ordenada. `partidos` son los jugados de sus equipos (pueden ser
    contra equipos de otra serie). `sorteo`: equipo → lugar que salió (1 es el mejor)."""
    tarjetas = tarjetas or {}
    sorteo = sorteo or {}
    generales = {
        e: replace(f, tarjetas=tarjetas.get(e, Tarjetas()))
        for e, f in _filas(equipos, partidos, puntos).items()
    }

    def desempatar(grupo: list[Equipo]) -> list[tuple[Equipo, bool]]:
        """El grupo empatado, en orden; con True los que dependen de un sorteo que falta."""
        if len(grupo) == 1:
            return [(grupo[0], False)]
        clave: dict[Equipo, tuple[int, ...]]
        if criterio == "diferencia_de_gol":
            clave = {e: (-generales[e].dg, -generales[e].gf) for e in grupo}
        else:
            conjunto = set(grupo)
            entre_ellos = [p for p in partidos if {p.local, p.visitante} <= conjunto]
            usados = entre_ellos if _jugaron_todos(conjunto, partidos) else partidos
            parciales = _filas(grupo, usados, puntos)
            clave = {
                e: (
                    -parciales[e].puntos,
                    -parciales[e].gf,
                    parciales[e].gc,
                    generales[e].tarjetas.total,
                )
                for e in grupo
            }
        return _por_clave(grupo, clave, desempatar, sorteo)

    ordenados: list[tuple[Equipo, bool]] = []
    for valor in sorted({f.puntos for f in generales.values()}, reverse=True):
        ordenados += desempatar([e for e in equipos if generales[e].puntos == valor])
    return [
        replace(generales[e], posicion=i, falta_sorteo=falta)
        for i, (e, falta) in enumerate(ordenados, start=1)
    ]


def _por_clave(
    grupo: list[Equipo],
    clave: dict[Equipo, tuple[int, ...]],
    desempatar: _Desempate,
    sorteo: Mapping[Equipo, int],
) -> list[tuple[Equipo, bool]]:
    """Ordena por la clave; los que empatan se vuelven a desempatar entre ellos. Si un
    criterio no separa a nadie, decide el sorteo, o queda marcado que falta."""
    resultado: list[tuple[Equipo, bool]] = []
    for valor in sorted(set(clave.values())):
        empatados = [e for e in grupo if clave[e] == valor]
        if len(empatados) == len(grupo) and len(grupo) > 1:
            if all(e in sorteo for e in grupo):
                resultado += [(e, False) for e in sorted(grupo, key=lambda e: sorteo[e])]
            else:
                resultado += [(e, True) for e in grupo]
        else:
            resultado += desempatar(empatados)
    return resultado


def mejores(candidatos: Sequence[Fila]) -> list[Fila]:
    """P26: el mejor 3.º o el mejor perdedor entre series: más puntos por partido jugado y
    después mejor diferencia de gol."""

    def clave(f: Fila) -> tuple[Fraction, int]:
        return (Fraction(f.puntos, f.pj) if f.pj else Fraction(0), f.dg)

    return sorted(candidatos, key=clave, reverse=True)
