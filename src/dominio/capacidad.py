"""Capacidad antes de programar (PRO-14; ARQUITECTURA 8): ¿entran los partidos en las canchas?

Cada cancha entera (C1, C2, C3) es un recurso con los minutos que dan sus franjas. Un partido
en una mitad ocupa media cancha. Un flujo máximo reparte lo que pide cada categoría entre sus
canchas compatibles: si el flujo no llega a lo pedido, no entra, aunque los totales alcancen.

Aproximación: si una categoría juega en mitades de una cancha y entera en otra, se cuenta
como si ocupara media cancha en todas (lo más optimista). Si así no entra, seguro no entra.
"""

from collections import defaultdict
from dataclasses import dataclass

from ortools.graph.python import max_flow  # type: ignore[import-untyped]  # sin tipos

_INFINITO = 10**12


@dataclass(frozen=True)
class Demanda:
    categoria: str
    minutos: int  # partidos por turno
    canchas: frozenset[str]  # códigos compatibles, enteras o mitades


@dataclass(frozen=True)
class GrupoDeCanchas:
    """Canchas conectadas por la compatibilidad, con lo que piden y lo que dan (en minutos)."""

    canchas: tuple[str, ...]
    categorias: tuple[str, ...]
    pedido: int
    disponible: int
    ubicable: int

    @property
    def entra(self) -> bool:
        return self.ubicable >= self.pedido

    @property
    def faltan(self) -> int:
        return max(self.pedido - self.ubicable, 0)


def calcular_capacidad(
    demandas: list[Demanda], padres: dict[str, str | None], oferta: dict[str, int]
) -> list[GrupoDeCanchas]:
    """`padres` dice de qué cancha es mitad cada código (None si es entera); `oferta`, los
    minutos de cada cancha entera. Todo se cuenta en medios minutos para usar enteros."""
    demandas = [d for d in demandas if d.minutos > 0]
    if not demandas:
        return []

    # Cada categoría: a qué canchas enteras puede ir y cuánto ocupa (en medios minutos).
    destinos: dict[str, set[str]] = {}
    pedido: dict[str, int] = {}
    for demanda in demandas:
        enteras = {padres.get(c) or c for c in demanda.canchas}
        en_mitades = any(padres.get(c) for c in demanda.canchas)
        destinos[demanda.categoria] = enteras
        pedido[demanda.categoria] = demanda.minutos * (1 if en_mitades else 2)

    orden = [d.categoria for d in demandas]  # las categorías, en el orden en que llegan
    grupos = _componentes(destinos)
    flujo = max_flow.SimpleMaxFlow()
    nodos = {nombre: i for i, nombre in enumerate(["fuente", "sumidero", *destinos])}
    for cancha in sorted({c for enteras in destinos.values() for c in enteras}):
        nodos[f"cancha {cancha}"] = len(nodos)
        flujo.add_arc_with_capacity(
            nodos[f"cancha {cancha}"], nodos["sumidero"], 2 * oferta.get(cancha, 0)
        )
    arco_de: dict[str, int] = {}
    for categoria, enteras in destinos.items():
        arco_de[categoria] = flujo.add_arc_with_capacity(
            nodos["fuente"], nodos[categoria], pedido[categoria]
        )
        for cancha in enteras:
            flujo.add_arc_with_capacity(nodos[categoria], nodos[f"cancha {cancha}"], _INFINITO)
    if flujo.solve(nodos["fuente"], nodos["sumidero"]) != flujo.OPTIMAL:
        raise RuntimeError("El flujo máximo no terminó: no debería pasar con datos finitos")

    resultado = []
    for categorias, canchas in grupos:
        pedido_total = sum(pedido[c] for c in categorias)
        ubicado = sum(flujo.flow(arco_de[c]) for c in categorias)
        resultado.append(
            GrupoDeCanchas(
                canchas=tuple(sorted(canchas)),
                categorias=tuple(c for c in orden if c in categorias),
                pedido=(pedido_total + 1) // 2,
                disponible=sum(oferta.get(c, 0) for c in canchas),
                ubicable=ubicado // 2,
            )
        )
    return sorted(resultado, key=lambda g: g.canchas)


def _componentes(destinos: dict[str, set[str]]) -> list[tuple[set[str], set[str]]]:
    """Grupos de categorías y canchas conectados por la compatibilidad."""
    padre: dict[str, str] = {}

    def raiz(x: str) -> str:
        padre.setdefault(x, x)
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    for categoria, canchas in destinos.items():
        raiz(f"cat:{categoria}")
        for cancha in canchas:
            padre[raiz(f"cat:{categoria}")] = raiz(f"can:{cancha}")

    por_raiz: dict[str, tuple[set[str], set[str]]] = defaultdict(lambda: (set(), set()))
    for nodo in list(padre):
        categorias, canchas = por_raiz[raiz(nodo)]
        tipo, nombre = nodo.split(":", 1)
        (categorias if tipo == "cat" else canchas).add(nombre)
    return list(por_raiz.values())
