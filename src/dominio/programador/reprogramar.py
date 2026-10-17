"""Propuestas de reprogramación (PRO-13; ARQUITECTURA 8).

Ante un bloqueo nuevo, una suspensión o un partido sin lugar, se resuelve el mismo modelo
partiendo del calendario actual, con otro objetivo: mover la menor cantidad de partidos,
afectar a la menor cantidad de equipos y preferir el mismo fin de semana. Solo se mueven los
partidos de una ventana (ese fin de semana y el siguiente), y solo dentro de ella; el resto
queda fijo, igual que lo que la organización puso a mano fuera de las franjas (T11.2).
Para dar 2 o 3 propuestas distintas (T13.18), después de cada solución se pide que al menos
uno de los partidos que se movieron quede a un turno o más de donde lo puso esa solución, sin
mover más partidos que la primera: las alternativas son otros horarios u otros días para lo
mismo, no movimientos de más. Si no hay otra, se devuelven las que hay.

T13.42: lo que estaba sin lugar se intenta ubicar solo si se pide (`ubicar`). Para un bloqueo no
se pide: con un calendario a medio programar, ubicarlo todo agrandaba el problema y daba
propuestas de decenas de movimientos. Y si el solver no termina, la búsqueda lo dice
(`sin_terminar`), en lugar de un "no hay forma".
"""

from collections import defaultdict
from collections.abc import Hashable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime

from ortools.sat.python import cp_model

from dominio.programador.modelo import PASO_MIN, Equipo, Modelo, Problema, lugar_habitual
from dominio.verificador import FranjaExtra

Lugar = tuple[str, datetime]  # cancha e inicio


@dataclass(frozen=True)
class Movimiento:
    partido: Hashable
    antes: Lugar | None  # None si estaba sin ubicar
    despues: Lugar


@dataclass(frozen=True)
class Propuesta:
    movimientos: tuple[Movimiento, ...]

    def calendario(self, actual: dict[Hashable, Lugar]) -> dict[Hashable, Lugar]:
        """El calendario con esta propuesta aplicada."""
        return {**actual, **{m.partido: m.despues for m in self.movimientos}}


@dataclass(frozen=True)
class Busqueda:
    propuestas: list[Propuesta]
    sin_terminar: bool  # el solver no terminó antes de encontrar la primera


def proponer(
    problema: Problema,
    actual: dict[Hashable, Lugar],
    *,
    desde: datetime,
    hasta: datetime,
    cuantas: int = 3,
    segundos: float = 20,
    trabajadores: int = 8,
    preferidas: Sequence[FranjaExtra] = (),
) -> list[Propuesta]:
    """Las propuestas de `buscar_propuestas`, ubicando también lo que estaba sin lugar."""
    return buscar_propuestas(
        problema,
        actual,
        desde=desde,
        hasta=hasta,
        cuantas=cuantas,
        segundos=segundos,
        trabajadores=trabajadores,
        preferidas=preferidas,
    ).propuestas


def buscar_propuestas(
    problema: Problema,
    actual: dict[Hashable, Lugar],
    *,
    desde: datetime,
    hasta: datetime,
    cuantas: int = 3,
    segundos: float = 20,
    trabajadores: int = 8,
    preferidas: Sequence[FranjaExtra] = (),
    ubicar: frozenset[Hashable] | None = None,
) -> Busqueda:
    """Hasta `cuantas` propuestas distintas, de menos a más movimientos. Vacío si no hace
    falta mover nada o si no hay forma dentro de la ventana.

    B1 (fase 12): con `preferidas` (el tiempo que la organización eligió para jugar lo
    suspendido), lo que estaba sin lugar se ubica primero ahí; lo que no entra va a los días
    siguientes, moviendo lo menos posible. El resto del tiempo agregado se usa solo si hace
    falta. Con `ubicar`, de lo que estaba sin lugar se intenta ubicar solo eso (T13.42)."""
    movibles = {
        p.id
        for p in problema.partidos
        if p.fijo is None
        and (
            (p.id not in actual and (ubicar is None or p.id in ubicar))
            # T11.2: lo que la organización puso a mano fuera de lo habitual, queda.
            or (
                p.id in actual
                and desde <= actual[p.id][1] < hasta
                and lugar_habitual(problema, p, actual[p.id])
            )
        )
    }
    quietos = tuple(
        replace(p, fijo=actual[p.id]) if p.id not in movibles and p.id in actual else p
        for p in problema.partidos
    )
    modelo = Modelo(replace(problema, partidos=quietos))
    modelo.variables()
    modelo.canchas()
    modelo.equipos()
    modelo.grupos_y_llaves_por_dia()
    modelo.personas()
    modelo.orden()
    m, reloj = modelo.modelo, modelo.reloj
    for partido in quietos:
        if partido.id not in actual and partido.id not in movibles:
            m.add(modelo.presente[partido.id] == 0)  # sigue sin lugar
    primero, ultimo = reloj.paso(desde, hacia_arriba=True), reloj.paso(hasta, hacia_arriba=False)

    movido: dict[Hashable, cp_model.IntVar] = {}
    nuevos = []
    costo_de_semana = []
    costo_de_dia = []  # T13.42: mejor el mismo día, si hay lugar
    por_equipo: dict[Equipo, list[cp_model.IntVar]] = defaultdict(list)
    for partido in quietos:
        if partido.id not in movibles:
            continue
        presente, inicio = modelo.presente[partido.id], modelo.inicio[partido.id]
        m.add(inicio >= primero).only_enforce_if(presente)
        m.add(inicio <= ultimo).only_enforce_if(presente)
        if partido.id not in actual:
            nuevos.append(presente)  # estaba sin ubicar: se intenta ubicar
            continue
        m.add(presente == 1)  # lo que estaba ubicado sigue ubicado
        cancha, cuando = actual[partido.id]
        se_mueve = m.new_bool_var(f"mueve {partido.id}")
        movido[partido.id] = se_mueve
        m.add(inicio == reloj.paso(cuando, hacia_arriba=False)).only_enforce_if(se_mueve.Not())
        en_cancha = modelo.en_cancha[partido.id]
        if cancha in en_cancha:
            m.add(en_cancha[cancha] == 1).only_enforce_if(se_mueve.Not())
        else:
            m.add(se_mueve == 1)
        semana = cuando.isocalendar()[:2]
        for dia, en_dia in modelo.en_dia[partido.id].items():
            if dia.isocalendar()[:2] != semana:
                costo_de_semana.append(en_dia)
            elif dia != cuando.date():
                costo_de_dia.append(en_dia)
        for equipo in partido.equipos_definidos:
            por_equipo[equipo].append(se_mueve)

    afectados = []
    for equipo, suyos in por_equipo.items():
        afectado = m.new_bool_var(f"afectado {equipo}")
        m.add_max_equality(afectado, suyos)
        afectados.append(afectado)
    elegidas = set(preferidas)
    extra_no_elegido = []
    fuera_de_lo_elegido = []
    for partido in quietos:
        if partido.id not in movibles:
            continue
        de_este = modelo.extra_de.get(partido.id, [])
        extra_no_elegido += [v for e, v in de_este if e not in elegidas]
        if elegidas and partido.id not in actual:
            aca = [v for e, v in de_este if e in elegidas]
            en_elegida = m.new_bool_var(f"{partido.id} en lo elegido")
            m.add_max_equality(en_elegida, aca or [m.new_constant(0)])
            fuera_de_lo_elegido.append(modelo.presente[partido.id] - en_elegida)
    m.minimize(
        1000 * sum(movido.values())
        + 100 * sum(afectados)
        + 30 * sum(fuera_de_lo_elegido)
        + 60 * sum(extra_no_elegido)
        + 10 * sum(costo_de_semana)
        + 3 * sum(costo_de_dia)
        - 100_000 * sum(nuevos)
    )

    propuestas: list[Propuesta] = []
    sin_terminar = False
    for _ in range(cuantas):
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = segundos
        solver.parameters.num_workers = trabajadores
        estado = solver.solve(m)
        if estado not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            sin_terminar = not propuestas and estado == cp_model.UNKNOWN
            break
        movimientos = []
        for partido in quietos:
            if partido.id not in movibles or not solver.value(modelo.presente[partido.id]):
                continue
            if partido.id in movido and not solver.value(movido[partido.id]):
                continue
            cancha = next(c for c, v in modelo.en_cancha[partido.id].items() if solver.value(v))
            despues = (cancha, reloj.momento(solver.value(modelo.inicio[partido.id])))
            movimientos.append(Movimiento(partido.id, actual.get(partido.id), despues))
        if not movimientos:
            break
        propuestas.append(Propuesta(tuple(movimientos)))
        if len(propuestas) == 1:
            # T13.18: las alternativas no mueven más partidos que la primera.
            m.add(sum(movido.values()) <= sum(1 for mv in movimientos if mv.antes is not None))
        # La próxima: alguno de estos, a un turno o más de donde quedó en esta.
        lejos: list[cp_model.IntVar] = []
        por_id = {p.id: p for p in quietos}
        for mv in movimientos:
            inicio = modelo.inicio[mv.partido]
            paso = reloj.paso(mv.despues[1], hacia_arriba=False)
            turno = -(-por_id[mv.partido].minutos_turno // PASO_MIN)
            mas_temprano, mas_tarde = m.new_bool_var(""), m.new_bool_var("")
            m.add(inicio <= paso - turno).only_enforce_if(mas_temprano)
            m.add(inicio >= paso + turno).only_enforce_if(mas_tarde)
            lejos += [mas_temprano, mas_tarde]
        m.add_bool_or(lejos)
    return Busqueda(sorted(propuestas, key=lambda p: len(p.movimientos)), sin_terminar)
