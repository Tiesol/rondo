"""Prueba de riesgo T0.6: un modelo CP-SAT sintético con la forma del problema real.

Mide cuánto tarda el solver con una CPU débil (Render gratis: 0,1 CPU). No usa la
configuración real del torneo y se borra al cerrar la fase 4, cuando exista el programador.
"""

import random
import time
from dataclasses import dataclass
from itertools import combinations

from ortools.sat.python import cp_model

PASO_MIN = 5
PASOS_POR_DIA = 24 * 60 // PASO_MIN

# Cancha que se elige → canchas físicas que ocupa. C1 entera ocupa sus dos mitades.
RECURSOS: dict[str, frozenset[str]] = {
    "C1": frozenset({"C1A", "C1B"}),
    "C1A": frozenset({"C1A"}),
    "C1B": frozenset({"C1B"}),
    "C2": frozenset({"C2"}),
    "C3": frozenset({"C3"}),
}

# Tipo de categoría → (turno en minutos, canchas compatibles). Como en 4.1, 4.4 y 6.1.
TIPOS: dict[str, tuple[int, tuple[str, ...]]] = {
    "mitades": (40, ("C1A", "C1B")),
    "F7": (50, ("C1", "C2")),
    "F8": (50, ("C1",)),
    "F11": (70, ("C3",)),
}


@dataclass(frozen=True, slots=True)
class Division:
    tipo: str
    equipos: int


@dataclass(frozen=True, slots=True)
class Partido:
    id: int
    equipos: tuple[int, int]
    turno: int  # en pasos de 5 minutos
    canchas: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Instancia:
    partidos: tuple[Partido, ...]
    franjas: tuple[tuple[int, int], ...]  # (inicio, fin) en pasos desde el primer viernes
    pares_de_profes: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class Asignacion:
    partido: int
    cancha: str
    inicio: int


@dataclass(frozen=True, slots=True)
class Resultado:
    estado: str
    segundos_hasta_primera: float | None
    segundos_totales: float
    asignaciones: tuple[Asignacion, ...]


def _franjas(findes: int) -> tuple[tuple[int, int], ...]:
    """Viernes de 16 a 20 y sábado y domingo de 8 a 16, en pasos desde el primer viernes."""

    def en_pasos(dia: int, hora: int) -> int:
        return dia * PASOS_POR_DIA + hora * 60 // PASO_MIN

    franjas: list[tuple[int, int]] = []
    for semana in range(findes):
        viernes = semana * 7
        franjas.append((en_pasos(viernes, 16), en_pasos(viernes, 20)))
        for dia in (viernes + 1, viernes + 2):
            franjas.append((en_pasos(dia, 8), en_pasos(dia, 16)))
    return tuple(franjas)


def _cruces_de_grupos(equipos: list[int]) -> list[tuple[int, int]]:
    """Cruces de la fase de grupos según la tabla 4.5 (aproximada, solo para medir)."""
    n = len(equipos)
    if n == 3:  # todos contra todos, ida y vuelta
        return list(combinations(equipos, 2)) * 2
    if n in (6, 7):  # series cruzadas: cada uno de A contra cada uno de B
        mitad = (n + 1) // 2
        return [(a, b) for a in equipos[:mitad] for b in equipos[mitad:]]
    if n >= 8:  # dos series, todos contra todos dentro de cada una
        mitad = n // 2
        return list(combinations(equipos[:mitad], 2)) + list(combinations(equipos[mitad:], 2))
    return list(combinations(equipos, 2))


def generar_instancia(
    divisiones: list[Division], findes: int, pares_de_profes: int, semilla: int
) -> Instancia:
    """Fase de grupos de cada división y pares de equipos con un profe en común."""
    azar = random.Random(semilla)
    partidos: list[Partido] = []
    equipos_por_division: list[list[int]] = []
    siguiente_equipo = 0
    for division in divisiones:
        minutos, canchas = TIPOS[division.tipo]
        equipos = list(range(siguiente_equipo, siguiente_equipo + division.equipos))
        siguiente_equipo += division.equipos
        equipos_por_division.append(equipos)
        for a, b in _cruces_de_grupos(equipos):
            partidos.append(Partido(len(partidos), (a, b), minutos // PASO_MIN, canchas))

    pares: set[tuple[int, int]] = set()
    while len(pares) < pares_de_profes and len(equipos_por_division) > 1:
        div_x, div_y = azar.sample(range(len(equipos_por_division)), 2)
        x = azar.choice(equipos_por_division[div_x])
        y = azar.choice(equipos_por_division[div_y])
        pares.add((min(x, y), max(x, y)))
    return Instancia(tuple(partidos), _franjas(findes), tuple(sorted(pares)))


class _PrimeraSolucion(cp_model.CpSolverSolutionCallback):
    def __init__(self, reloj: float) -> None:
        super().__init__()
        self._reloj = reloj
        self.segundos: float | None = None

    def on_solution_callback(self) -> None:
        if self.segundos is None:
            self.segundos = time.perf_counter() - self._reloj


def resolver(instancia: Instancia, segundos: float, workers: int) -> Resultado:
    modelo = cp_model.CpModel()
    inicios: dict[int, cp_model.IntVar] = {}
    eleccion: dict[tuple[int, str], cp_model.IntVar] = {}
    por_recurso: dict[str, list[cp_model.IntervalVar]] = {r: [] for r in ("C1A", "C1B", "C2", "C3")}
    del_partido: dict[int, cp_model.IntervalVar] = {}
    por_equipo: dict[int, list[cp_model.IntervalVar]] = {}

    for p in instancia.partidos:
        # El turno entero (partido y cambio) cabe dentro de una franja.
        dominio = cp_model.Domain.from_intervals(
            [[ini, fin - p.turno] for ini, fin in instancia.franjas if fin - ini >= p.turno]
        )
        inicio = modelo.new_int_var_from_domain(dominio, f"inicio_{p.id}")
        inicios[p.id] = inicio
        del_partido[p.id] = modelo.new_fixed_size_interval_var(inicio, p.turno, f"turno_{p.id}")
        # Para cada equipo, el turno se alarga uno más: deja un turno libre en medio (P17).
        con_descanso = modelo.new_fixed_size_interval_var(inicio, 2 * p.turno, f"desc_{p.id}")
        for equipo in p.equipos:
            por_equipo.setdefault(equipo, []).append(con_descanso)

        opciones = []
        for cancha in p.canchas:
            elegida = modelo.new_bool_var(f"cancha_{p.id}_{cancha}")
            eleccion[(p.id, cancha)] = elegida
            opciones.append(elegida)
            intervalo = modelo.new_optional_fixed_size_interval_var(
                inicio, p.turno, elegida, f"en_{p.id}_{cancha}"
            )
            for recurso in RECURSOS[cancha]:
                por_recurso[recurso].append(intervalo)
        modelo.add_exactly_one(opciones)

    for intervalos in por_recurso.values():
        modelo.add_no_overlap(intervalos)
    for intervalos in por_equipo.values():
        modelo.add_no_overlap(intervalos)
    for x, y in instancia.pares_de_profes:
        compartidos = [
            del_partido[p.id] for p in instancia.partidos if x in p.equipos or y in p.equipos
        ]
        modelo.add_no_overlap(compartidos)

    # Un objetivo cualquiera, para que el solver también optimice: jugar lo antes posible.
    modelo.minimize(sum(inicios.values()))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = segundos
    solver.parameters.num_workers = workers
    reloj = time.perf_counter()
    primera = _PrimeraSolucion(reloj)
    estado = solver.solve(modelo, primera)
    total = time.perf_counter() - reloj

    asignaciones: tuple[Asignacion, ...] = ()
    if estado in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        asignaciones = tuple(
            Asignacion(
                p.id,
                next(c for c in p.canchas if solver.value(eleccion[(p.id, c)])),
                solver.value(inicios[p.id]),
            )
            for p in instancia.partidos
        )
    return Resultado(solver.status_name(estado), primera.segundos, total, asignaciones)
