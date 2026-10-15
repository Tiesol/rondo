"""Tablas de posiciones de una categoría (T8.7): una por serie, o una sola si no hay series.

Cuenta solo los partidos de grupos terminados. El resultado de cada uno sale de sus eventos
(dominio.partido); las tarjetas, del fair play. Pocas consultas: todo de una vez.
"""

from dataclasses import dataclass, field, replace
from typing import Any

from django.db import transaction
from django.db.models import Prefetch

from dominio.config import Reglas
from dominio.partido import Evento as EventoDelDominio
from dominio.partido import resultado
from dominio.tabla import Fila, Jugado, Tarjetas, tabla
from torneo.models import CategoriaNivel, Equipo, Evento, Partido, SorteoDeTabla


@dataclass
class TablaDeSerie:
    nombre: str  # "A", "B" o "" si la categoría es un solo grupo
    filas: list[Fila]
    equipos: dict[Any, Equipo] = field(default_factory=dict)

    @property
    def con_equipos(self) -> list[tuple[Fila, Equipo]]:
        return [(f, self.equipos[f.equipo]) for f in self.filas]

    @property
    def falta_sorteo(self) -> list[Equipo]:
        return [self.equipos[f.equipo] for f in self.filas if f.falta_sorteo]


def _jugados(categoria: CategoriaNivel, reglas: Reglas) -> tuple[list[Jugado], dict[Any, Tarjetas]]:
    partidos = categoria.partidos.filter(
        fase=Partido.Fase.GRUPOS, estado=Partido.Estado.JUGADO
    ).prefetch_related(
        Prefetch("eventos", queryset=Evento.objects.only("tipo", "equipo_id", "partido_id"))
    )
    jugados = []
    amarillas: dict[Any, int] = {}
    rojas: dict[Any, int] = {}
    for p in partidos:
        if p.local_id is None or p.visitante_id is None:
            continue
        eventos = list(p.eventos.all())
        lado = {p.local_id: "local", p.visitante_id: "visitante"}
        r = resultado(
            [EventoDelDominio(e.tipo, lado[e.equipo_id]) for e in eventos],  # type: ignore[arg-type]
            no_se_presento=p.no_se_presento or None,  # type: ignore[arg-type]
            marcador_wo=reglas.marcador_wo,
        )
        jugados.append(Jugado(p.local_id, p.visitante_id, *r.marcador))
        for e in eventos:
            if e.tipo == Evento.Tipo.AMARILLA:
                amarillas[e.equipo_id] = amarillas.get(e.equipo_id, 0) + 1
            elif e.tipo == Evento.Tipo.ROJA:
                rojas[e.equipo_id] = rojas.get(e.equipo_id, 0) + 1
    equipos = set(amarillas) | set(rojas)
    tarjetas = {e: Tarjetas(amarillas.get(e, 0), rojas.get(e, 0)) for e in equipos}
    return jugados, tarjetas


def tablas_de(categoria: CategoriaNivel) -> list[TablaDeSerie]:
    reglas = Reglas.model_validate(categoria.torneo.reglas)
    jugados, tarjetas = _jugados(categoria, reglas)
    sorteo: dict[Any, int] = dict(
        SorteoDeTabla.objects.filter(categoria=categoria).values_list("equipo_id", "lugar")
    )
    todos = {e.pk: e for e in categoria.equipos.select_related("club")}
    series = [
        (s.nombre, [e.pk for e in s.equipos.all()])
        for s in categoria.series.prefetch_related("equipos")
    ] or [("", list(todos))]
    # T13.10: con partidos por jugar, los empatados están empatados; el sorteo se pide recién
    # cuando la serie terminó.
    por_jugar: set[Any] = set()
    for local, visitante in (
        categoria.partidos.filter(fase=Partido.Fase.GRUPOS)
        .exclude(estado=Partido.Estado.JUGADO)
        .values_list("local_id", "visitante_id")
    ):
        por_jugar |= {local, visitante}
    tablas = []
    for nombre, pks in series:
        filas = tabla(
            pks,
            jugados,
            puntos=reglas.puntos_por_partido,
            tarjetas=tarjetas,
            sorteo=sorteo,
            criterio=reglas.criterio_de_desempate,
        )
        if por_jugar & set(pks):
            filas = [replace(f, falta_sorteo=False) for f in filas]
        tablas.append(TablaDeSerie(nombre, filas, {pk: todos[pk] for pk in pks if pk in todos}))
    return tablas


@transaction.atomic
def registrar_sorteo(categoria: CategoriaNivel, orden: list[Equipo]) -> None:
    """P28: el lugar que salió en el sorteo para cada equipo empatado (el primero, el mejor)."""
    for lugar, equipo in enumerate(orden, start=1):
        SorteoDeTabla.objects.update_or_create(
            categoria=categoria, equipo=equipo, defaults={"lugar": lugar}
        )
