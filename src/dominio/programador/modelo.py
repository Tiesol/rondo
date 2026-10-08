"""El programador (ARQUITECTURA 8): un modelo CP-SAT en pasos de 5 minutos.

Cada partido elige un inicio dentro de una franja (el partido termina adentro, P48) y una
cancha compatible, o queda sin ubicar: así el solver siempre devuelve el mejor calendario
posible, y lo que no entra se informa con su motivo (motivos.py).

Restricciones duras:

- canchas (PRO-01): cada cancha física tiene un turno a la vez; C1 entera ocupa C1A y C1B;
- compatibilidad (PRO-02) y franjas (PRO-03): ya están en los valores posibles;
- equipos (PRO-04): no se pisan, dejan los turnos libres del día (P17) y no pasan del
  máximo de partidos por día (P47);
- fijos (PRO-10): los partidos jugados o fijados a mano no se mueven.
"""

import time
from collections import defaultdict
from collections.abc import Hashable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from ortools.sat.python import cp_model

from dominio.config import Reglas

PASO_MIN = 5
Equipo = Hashable


@dataclass(frozen=True)
class PartidoAProgramar:
    id: Hashable
    categoria: str
    equipos: tuple[Equipo | None, Equipo | None]  # None mientras esté por definir
    minutos_partido: int
    minutos_turno: int
    canchas: frozenset[str]  # las compatibles
    fijo: tuple[str, datetime] | None = None  # cancha e inicio que no se tocan

    @property
    def equipos_definidos(self) -> tuple[Equipo, ...]:
        return tuple(e for e in self.equipos if e is not None)


@dataclass(frozen=True)
class Problema:
    partidos: tuple[PartidoAProgramar, ...]
    fisicas: dict[str, frozenset[str]]  # cancha → canchas físicas que ocupa
    franjas: tuple[tuple[datetime, datetime], ...]
    reglas: Reglas


@dataclass
class Resultado:
    ubicados: dict[Hashable, tuple[str, datetime]] = field(default_factory=dict)
    sin_ubicar: list[Hashable] = field(default_factory=list)
    estado: str = ""
    segundos: float = 0.0


class _Reloj:
    """Pasa de fecha y hora a pasos de 5 minutos desde el primer día, y al revés."""

    def __init__(self, franjas: tuple[tuple[datetime, datetime], ...]) -> None:
        self.origen = min(desde for desde, _ in franjas).replace(hour=0, minute=0)

    def paso(self, momento: datetime, *, hacia_arriba: bool) -> int:
        minutos = (momento - self.origen).total_seconds() / 60
        cociente, resto = divmod(minutos, PASO_MIN)
        return int(cociente) + (1 if hacia_arriba and resto else 0)

    def momento(self, paso: int) -> datetime:
        return self.origen + timedelta(minutes=paso * PASO_MIN)


def _pasos(minutos: int) -> int:
    return -(-minutos // PASO_MIN)  # hacia arriba


class _Modelo:
    def __init__(self, problema: Problema) -> None:
        self.problema = problema
        self.modelo = cp_model.CpModel()
        self.reloj = _Reloj(problema.franjas)
        # Días de juego: la ventana de inicios posibles de cada día, en pasos.
        self.dias: dict[date, list[tuple[int, int]]] = defaultdict(list)
        for desde, hasta in problema.franjas:
            self.dias[desde.date()].append(
                (
                    self.reloj.paso(desde, hacia_arriba=True),
                    self.reloj.paso(hasta, hacia_arriba=False),
                )
            )
        self.presente: dict[Hashable, cp_model.IntVar] = {}
        self.inicio: dict[Hashable, cp_model.IntVar] = {}
        self.en_cancha: dict[Hashable, dict[str, cp_model.IntVar]] = {}
        self.en_dia: dict[Hashable, dict[date, cp_model.IntVar]] = {}

    def _inicios_posibles(self, partido: PartidoAProgramar) -> list[tuple[int, int]]:
        largo = _pasos(partido.minutos_partido)
        ventanas = []
        for desde, hasta in self.problema.franjas:
            primero = self.reloj.paso(desde, hacia_arriba=True)
            ultimo = self.reloj.paso(hasta, hacia_arriba=False) - largo
            if ultimo >= primero:
                ventanas.append((primero, ultimo))
        return ventanas

    def variables(self) -> None:
        m = self.modelo
        for partido in self.problema.partidos:
            ventanas = self._inicios_posibles(partido)
            if partido.fijo:
                fijo = self.reloj.paso(partido.fijo[1], hacia_arriba=False)
                ventanas.append((fijo, fijo))
            if not ventanas:
                ventanas = [(0, 0)]  # no entra en ninguna franja: queda sin ubicar
            presente = m.new_bool_var(f"presente {partido.id}")
            inicio = m.new_int_var_from_domain(
                cp_model.Domain.from_intervals([list(v) for v in ventanas]), f"inicio {partido.id}"
            )
            self.presente[partido.id], self.inicio[partido.id] = presente, inicio

            canchas = sorted(partido.canchas & set(self.problema.fisicas))
            self.en_cancha[partido.id] = {
                c: m.new_bool_var(f"{partido.id} en {c}") for c in canchas
            }
            m.add(sum(self.en_cancha[partido.id].values()) == presente)

            self.en_dia[partido.id] = {}
            for dia, rangos in self.dias.items():
                en_dia = m.new_bool_var(f"{partido.id} el {dia}")
                m.add(inicio >= min(r[0] for r in rangos)).only_enforce_if(en_dia)
                m.add(inicio <= max(r[1] for r in rangos)).only_enforce_if(en_dia)
                self.en_dia[partido.id][dia] = en_dia
            m.add(sum(self.en_dia[partido.id].values()) == presente)

            if partido.fijo:
                cancha, momento = partido.fijo
                m.add(presente == 1)
                m.add(inicio == self.reloj.paso(momento, hacia_arriba=False))
                if cancha in self.en_cancha[partido.id]:
                    m.add(self.en_cancha[partido.id][cancha] == 1)
                else:  # fijado en una cancha que no es compatible: se respeta igual
                    self.en_cancha[partido.id][cancha] = m.new_constant(1)

    def canchas(self) -> None:
        por_unidad: dict[str, list[cp_model.IntervalVar]] = defaultdict(list)
        for partido in self.problema.partidos:
            turno = _pasos(partido.minutos_turno)
            for cancha, elegida in self.en_cancha[partido.id].items():
                intervalo = self.modelo.new_optional_fixed_size_interval_var(
                    self.inicio[partido.id], turno, elegida, f"{partido.id} ocupa {cancha}"
                )
                for unidad in self.problema.fisicas.get(cancha, frozenset({cancha})):
                    por_unidad[unidad].append(intervalo)
        for intervalos in por_unidad.values():
            self.modelo.add_no_overlap(intervalos)

    def equipos(self) -> None:
        reglas = self.problema.reglas
        por_equipo: dict[Equipo, list[PartidoAProgramar]] = defaultdict(list)
        for partido in self.problema.partidos:
            for equipo in partido.equipos_definidos:
                por_equipo[equipo].append(partido)
        for suyos in por_equipo.values():
            # El turno más los turnos libres del día (P17): de un día al siguiente sobra lugar.
            self.modelo.add_no_overlap(
                [
                    self.modelo.new_optional_fixed_size_interval_var(
                        self.inicio[p.id],
                        _pasos(p.minutos_turno) * (1 + reglas.turnos_libres_mismo_dia),
                        self.presente[p.id],
                        f"equipo en {p.id}",
                    )
                    for p in suyos
                ]
            )
            for dia in self.dias:
                self.modelo.add(
                    sum(self.en_dia[p.id][dia] for p in suyos) <= reglas.max_partidos_por_dia
                )

    def objetivo(self) -> None:
        self.modelo.maximize(sum(self.presente.values()))

    def resolver(self, segundos: float, trabajadores: int, semilla: int) -> Resultado:
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = segundos
        solver.parameters.num_workers = trabajadores
        solver.parameters.random_seed = semilla
        comienzo = time.monotonic()
        estado = solver.solve(self.modelo)
        resultado = Resultado(estado=solver.status_name(estado))
        resultado.segundos = round(time.monotonic() - comienzo, 2)
        hay_solucion = estado in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        for partido in self.problema.partidos:
            if hay_solucion and solver.value(self.presente[partido.id]):
                cancha = next(c for c, v in self.en_cancha[partido.id].items() if solver.value(v))
                inicio = self.reloj.momento(solver.value(self.inicio[partido.id]))
                resultado.ubicados[partido.id] = (cancha, inicio)
            else:
                resultado.sin_ubicar.append(partido.id)
        return resultado


def programar(
    problema: Problema, *, segundos: float = 60, trabajadores: int = 8, semilla: int = 0
) -> Resultado:
    """El mejor calendario que encuentra el solver en el tiempo dado."""
    if not problema.partidos:
        return Resultado(estado="OPTIMAL")
    modelo = _Modelo(problema)
    modelo.variables()
    modelo.canchas()
    modelo.equipos()
    modelo.objetivo()
    return modelo.resolver(segundos, trabajadores, semilla)
