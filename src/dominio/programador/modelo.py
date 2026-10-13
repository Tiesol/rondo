"""El programador (ARQUITECTURA 8): un modelo CP-SAT en pasos de 5 minutos.

Cada partido elige un inicio dentro de una franja (el partido termina adentro, P48) y una
cancha compatible, o queda sin ubicar: así el solver siempre devuelve el mejor calendario
posible, y lo que no entra se informa con su motivo (motivos.py).

Restricciones duras:

- canchas (PRO-01): cada cancha física tiene un turno a la vez; C1 entera ocupa C1A y C1B;
- compatibilidad (PRO-02) y franjas (PRO-03): ya están en los valores posibles;
- equipos (PRO-04): no se pisan, dejan los turnos libres del día (P17) y no pasan del
  máximo de partidos por día (P47). En la eliminación también los equipos virtuales: el
  ganador o el perdedor de una llave juega la llave que lo usa (T7.1);
- personas (PRO-05 y PRO-06): dos equipos que comparten un jugador no se pisan; si comparten
  un profe y juegan en canchas distintas, además dejan el margen para cambiar (P35).
  Seguidos en la misma cancha está bien (P18, CONTEXTO 6.4);
- bloqueos de la ACF (PRO-07): fuera de los inicios posibles;
- orden (PRO-08, si la regla es "dura"): las fechas de cada equipo van en orden (P19);
- eliminación (PRO-09): después de la fase de grupos de su categoría y de los partidos a
  los que se refiere (sin ellos no se ubica), y desde su fin de semana (P33). Si toma
  posiciones de grupo y cae el mismo día que partidos de grupos, deja el turno libre (P17);
- fijos (PRO-10): los partidos jugados o fijados a mano no se mueven.

Objetivo: primero ubicar la mayor cantidad; después, cada fecha de grupos cerca de su fin de
semana, para repartir la carga (PRO-12), poca espera de los profes compartidos (PRO-11), los
chicos temprano (P56), un solo partido por día por equipo (P17) y las finales en los dos últimos
días (P55).
"""

import time
from collections import defaultdict
from collections.abc import Hashable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from itertools import pairwise

from ortools.sat.python import cp_model

from dominio.config import Reglas
from dominio.verificador import Bloqueo, ParDeEquipos

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
    fase: str = "grupos"  # o "eliminacion"
    fecha: int | None = None  # en la fase de grupos
    clave: str = ""  # en la eliminación: "oro_semi_1"
    nombre: str = ""  # en la eliminación: "Semi 1 de Oro"
    despues_de: frozenset[str] = frozenset()  # claves de los partidos a los que se refiere
    virtuales: frozenset[str] = frozenset()  # en la eliminación: "ganador de la semi 1" (T7.1)
    toma_posiciones: bool = False  # en la eliminación: juega con equipos de la tabla de grupos
    dias_sin_jugar: frozenset[int] = frozenset()  # días de la semana (0 es lunes), P56
    temprano: bool = False  # de preferencia, en los primeros horarios del día (P56)

    @property
    def equipos_definidos(self) -> tuple[Equipo, ...]:
        return tuple(e for e in self.equipos if e is not None)

    @property
    def equipos_y_virtuales(self) -> tuple[Equipo, ...]:
        """Para las reglas de equipo (P17, P47): los definidos y los virtuales de las llaves."""
        return self.equipos_definidos + tuple(sorted(self.virtuales))


@dataclass(frozen=True)
class Problema:
    partidos: tuple[PartidoAProgramar, ...]
    fisicas: dict[str, frozenset[str]]  # cancha → canchas físicas que ocupa
    franjas: tuple[tuple[datetime, datetime], ...]
    reglas: Reglas
    pares: tuple[ParDeEquipos, ...] = ()
    bloqueos: tuple[Bloqueo, ...] = ()
    eliminacion_desde: datetime | None = None  # P33


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


class Modelo:
    """El modelo CP-SAT armado por partes; programar() y reprogramar.proponer() lo usan."""

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
        # Pares de partidos de equipos con un profe en común, y si el primero va antes (T7.3).
        self.profes_compartidos: list[
            tuple[PartidoAProgramar, PartidoAProgramar, cp_model.IntVar]
        ] = []

    def _inicios_posibles(self, partido: PartidoAProgramar) -> list[tuple[int, int]]:
        # P48: el partido termina dentro de la franja, o solo empieza dentro (último inicio).
        ultimo_inicio = self.problema.reglas.fin_de_franja == "ultimo_inicio"
        largo = 0 if ultimo_inicio else _pasos(partido.minutos_partido)
        ventanas = []
        for desde, hasta in self.problema.franjas:
            if desde.weekday() in partido.dias_sin_jugar:
                continue  # P56: esa categoría no juega ese día
            primero = self.reloj.paso(desde, hacia_arriba=True)
            ultimo = self.reloj.paso(hasta, hacia_arriba=False) - largo
            if ultimo >= primero:
                ventanas.append((primero, ultimo))
        return ventanas

    def _dominio(self, partido: PartidoAProgramar) -> cp_model.Domain:
        """Los inicios posibles: dentro de las franjas, fuera de los bloqueos de sus equipos
        y, en la eliminación, desde su fin de semana."""
        dominio = cp_model.Domain.from_intervals([list(v) for v in self._inicios_posibles(partido)])
        largo = _pasos(partido.minutos_partido)
        for bloqueo in self.problema.bloqueos:
            if bloqueo.equipo in partido.equipos_definidos:
                desde = self.reloj.paso(bloqueo.inicio, hacia_arriba=False) - largo + 1
                hasta = self.reloj.paso(bloqueo.fin, hacia_arriba=True) - 1
                dominio = dominio.intersection_with(cp_model.Domain(desde, hasta).complement())
        if partido.fase == "eliminacion" and self.problema.eliminacion_desde:
            desde = self.reloj.paso(self.problema.eliminacion_desde, hacia_arriba=True)
            dominio = dominio.intersection_with(cp_model.Domain(desde, cp_model.INT32_MAX))
        if partido.fijo:
            fijo = self.reloj.paso(partido.fijo[1], hacia_arriba=False)
            dominio = dominio.union_with(cp_model.Domain(fijo, fijo))
        return dominio

    def variables(self) -> None:
        m = self.modelo
        for partido in self.problema.partidos:
            dominio = self._dominio(partido)
            presente = m.new_bool_var(f"presente {partido.id}")
            if dominio.is_empty():  # no entra en ninguna franja: queda sin ubicar
                dominio = cp_model.Domain(0, 0)
                m.add(presente == 0)
            inicio = m.new_int_var_from_domain(dominio, f"inicio {partido.id}")
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
            for equipo in partido.equipos_y_virtuales:
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

    def personas(self) -> None:
        """Dos equipos que comparten a alguien no se pisan. Si es un profe y los partidos van
        en canchas distintas, además dejan el margen para cambiar (P35); seguidos en la
        misma cancha está bien (P18)."""
        por_equipo: dict[Equipo, list[PartidoAProgramar]] = defaultdict(list)
        for partido in self.problema.partidos:
            for equipo in partido.equipos_definidos:
                por_equipo[equipo].append(partido)
        margen = _pasos(self.problema.reglas.profe_minutos_cambio_de_cancha)
        separados: set[tuple[Hashable, Hashable]] = set()
        for par in self.problema.pares:
            juntos = {p.id: p for p in por_equipo.get(par.a, []) + por_equipo.get(par.b, [])}
            self.modelo.add_no_overlap(
                [
                    self.modelo.new_optional_fixed_size_interval_var(
                        self.inicio[p.id],
                        _pasos(p.minutos_partido),
                        self.presente[p.id],
                        f"{par.motivo} en {p.id}",
                    )
                    for p in juntos.values()
                ]
            )
            if par.motivo != "profe":
                continue
            for uno in por_equipo.get(par.a, []):
                for otro in por_equipo.get(par.b, []):
                    clave = (uno.id, otro.id) if str(uno.id) <= str(otro.id) else (otro.id, uno.id)
                    if uno.id != otro.id and clave not in separados:
                        separados.add(clave)
                        primero = self._margen_si_cambia_de_cancha(uno, otro, margen)
                        self.profes_compartidos.append((uno, otro, primero))

    def _margen_si_cambia_de_cancha(
        self, uno: PartidoAProgramar, otro: PartidoAProgramar, margen: int
    ) -> cp_model.IntVar:
        """Devuelve si `uno` va antes que `otro` (lo usa el objetivo de la espera)."""
        m = self.modelo
        canchas_uno, canchas_otro = self.en_cancha[uno.id], self.en_cancha[otro.id]
        misma = m.new_bool_var(f"{uno.id} y {otro.id} en la misma cancha")
        juntas = []
        for cancha in canchas_uno.keys() & canchas_otro.keys():
            ambas = m.new_bool_var(f"{uno.id} y {otro.id} en {cancha}")
            m.add_bool_and([canchas_uno[cancha], canchas_otro[cancha]]).only_enforce_if(ambas)
            m.add_bool_or([canchas_uno[cancha].Not(), canchas_otro[cancha].Not()]).only_enforce_if(
                ambas.Not()
            )
            juntas.append(ambas)
        m.add(sum(juntas) == misma)  # cada partido está en una sola cancha
        primero = m.new_bool_var(f"{uno.id} antes que {otro.id}")
        presentes = [self.presente[uno.id], self.presente[otro.id], misma.Not()]
        m.add(
            self.inicio[otro.id] >= self.inicio[uno.id] + _pasos(uno.minutos_partido) + margen
        ).only_enforce_if([*presentes, primero])
        m.add(
            self.inicio[uno.id] >= self.inicio[otro.id] + _pasos(otro.minutos_partido) + margen
        ).only_enforce_if([*presentes, primero.Not()])
        # Sin el margen, igual uno va antes que el otro (no se pisan).
        m.add(
            self.inicio[otro.id] >= self.inicio[uno.id] + _pasos(uno.minutos_partido)
        ).only_enforce_if([self.presente[uno.id], self.presente[otro.id], primero])
        m.add(
            self.inicio[uno.id] >= self.inicio[otro.id] + _pasos(otro.minutos_partido)
        ).only_enforce_if([self.presente[uno.id], self.presente[otro.id], primero.Not()])
        return primero

    def _esperas_de_profes(self) -> list[cp_model.IntVar]:
        """PRO-11: los pasos que espera un profe compartido entre sus partidos del mismo día,
        del final de un turno al inicio del siguiente."""
        m = self.modelo
        esperas = []
        for uno, otro, primero in self.profes_compartidos:
            mismo_dia = m.new_bool_var(f"{uno.id} y {otro.id} el mismo día")
            dias = []
            for dia in self.en_dia[uno.id].keys() & self.en_dia[otro.id].keys():
                ambos = m.new_bool_var(f"{uno.id} y {otro.id} el {dia}")
                m.add_bool_and(
                    [self.en_dia[uno.id][dia], self.en_dia[otro.id][dia]]
                ).only_enforce_if(ambos)
                m.add_bool_or(
                    [self.en_dia[uno.id][dia].Not(), self.en_dia[otro.id][dia].Not()]
                ).only_enforce_if(ambos.Not())
                dias.append(ambos)
            m.add(sum(dias) == mismo_dia)
            espera = m.new_int_var(0, self._pasos_por_dia, f"espera entre {uno.id} y {otro.id}")
            m.add(
                espera >= self.inicio[otro.id] - self.inicio[uno.id] - _pasos(uno.minutos_turno)
            ).only_enforce_if([mismo_dia, primero])
            m.add(
                espera >= self.inicio[uno.id] - self.inicio[otro.id] - _pasos(otro.minutos_turno)
            ).only_enforce_if([mismo_dia, primero.Not()])
            esperas.append(espera)
        return esperas

    def _dos_partidos_en_el_dia(self) -> list[cp_model.IntVar]:
        """P17/P47: dos partidos de un equipo el mismo día se permiten, pero mejor evitarlos.
        Uno por equipo y día en que juega dos veces."""
        por_equipo: dict[Equipo, list[PartidoAProgramar]] = defaultdict(list)
        for partido in self.problema.partidos:
            for equipo in partido.equipos_definidos:
                por_equipo[equipo].append(partido)
        dobles = []
        for equipo, suyos in por_equipo.items():
            if len(suyos) < 2:
                continue
            for dia in self.dias:
                doble = self.modelo.new_bool_var(f"{equipo} dos veces el {dia}")
                self.modelo.add(
                    sum(self.en_dia[p.id][dia] for p in suyos) <= 1 + doble * len(suyos)
                )
                dobles.append(doble)
        return dobles

    def _finales_antes_de_tiempo(self) -> list[cp_model.IntVar]:
        """P55: las finales, de preferencia en los dos últimos días (llega la premiación)."""
        ultimos = set(sorted(self.dias)[-2:])
        return [
            en_dia
            for partido in self.problema.partidos
            if "final" in partido.clave
            for dia, en_dia in self.en_dia[partido.id].items()
            if dia not in ultimos
        ]

    def _horarios_tempranos(self) -> list[cp_model.IntVar]:
        """P56: los pasos desde que empieza el día hasta el partido, para los que prefieren
        jugar temprano (Sub 5 y Sub 6)."""
        demoras = []
        for partido in self.problema.partidos:
            if not partido.temprano:
                continue
            demora = self.modelo.new_int_var(0, self._pasos_por_dia, f"demora de {partido.id}")
            for dia, en_dia in self.en_dia[partido.id].items():
                primero = min(r[0] for r in self.dias[dia])
                self.modelo.add(demora >= self.inicio[partido.id] - primero).only_enforce_if(en_dia)
            demoras.append(demora)
        return demoras

    @property
    def _pasos_por_dia(self) -> int:
        return max(
            max(r[1] for r in rangos) - min(r[0] for r in rangos) for rangos in self.dias.values()
        )

    def _despues(
        self, antes: PartidoAProgramar, despues: PartidoAProgramar, *, descanso: bool = False
    ) -> None:
        """`despues` empieza al terminar el turno de `antes`. Con descanso, si caen el mismo
        día, deja además los turnos libres de P17 (el equipo de una es el de la otra)."""
        ambos = [self.presente[antes.id], self.presente[despues.id]]
        turno = _pasos(antes.minutos_turno)
        self.modelo.add(self.inicio[despues.id] >= self.inicio[antes.id] + turno).only_enforce_if(
            ambos
        )
        if not descanso:
            return
        libres = self.problema.reglas.turnos_libres_mismo_dia
        desde = self.problema.eliminacion_desde
        for dia in self.dias:
            if desde is not None and dia < desde.date():
                continue  # la llave no puede caer ese día
            self.modelo.add(
                self.inicio[despues.id] >= self.inicio[antes.id] + turno * (1 + libres)
            ).only_enforce_if([*ambos, self.en_dia[antes.id][dia], self.en_dia[despues.id][dia]])

    def orden(self) -> None:
        partidos = self.problema.partidos
        if self.problema.reglas.orden_de_fechas == "dura":
            por_equipo: dict[Equipo, list[PartidoAProgramar]] = defaultdict(list)
            for partido in partidos:
                if partido.fase == "grupos" and partido.fecha is not None:
                    for equipo in partido.equipos_definidos:
                        por_equipo[equipo].append(partido)
            for suyos in por_equipo.values():
                suyos.sort(key=lambda p: p.fecha or 0)
                for antes, despues in pairwise(suyos):
                    if (antes.fecha or 0) < (despues.fecha or 0):
                        self._despues(antes, despues)

        por_clave = {(p.categoria, p.clave): p for p in partidos if p.clave}
        grupos_de: dict[str, list[PartidoAProgramar]] = defaultdict(list)
        for partido in partidos:
            if partido.fase == "grupos":
                grupos_de[partido.categoria].append(partido)
        for llave in (p for p in partidos if p.fase == "eliminacion"):
            for grupo in grupos_de[llave.categoria]:
                self._despues(grupo, llave, descanso=llave.toma_posiciones)
            for clave in llave.despues_de:
                anterior = por_clave.get((llave.categoria, clave))
                if anterior is None:
                    continue
                self._despues(anterior, llave)
                # Sin los partidos a los que se refiere, la llave no se juega.
                self.modelo.add_implication(self.presente[llave.id], self.presente[anterior.id])

    def objetivo(self) -> None:
        """Ubicar manda siempre. Después, que cada fecha caiga cerca de su fin de semana
        (PRO-12) y que los profes compartidos esperen poco entre sus partidos (PRO-11): una
        semana de desvío pesa como una hora de espera."""
        semanas = sorted({desde.isocalendar()[:2] for desde, _ in self.problema.franjas})
        if self.problema.eliminacion_desde:
            limite = self.problema.eliminacion_desde.isocalendar()[:2]
            semanas_de_grupos = [s for s in semanas if s < limite] or semanas
        else:
            semanas_de_grupos = semanas
        indice = {semana: i for i, semana in enumerate(semanas)}
        fechas: dict[str, int] = defaultdict(int)
        for partido in self.problema.partidos:
            if partido.fecha:
                fechas[partido.categoria] = max(fechas[partido.categoria], partido.fecha)

        desvio = []
        for partido in self.problema.partidos:
            if not partido.fecha:
                continue
            objetivo = (partido.fecha - 1) * len(semanas_de_grupos) // fechas[partido.categoria]
            for dia, en_dia in self.en_dia[partido.id].items():
                distancia = abs(indice[dia.isocalendar()[:2]] - objetivo)
                if distancia:
                    desvio.append(distancia * en_dia)
        esperas = self._esperas_de_profes()
        temprano = self._horarios_tempranos()
        dobles = self._dos_partidos_en_el_dia()
        finales = self._finales_antes_de_tiempo()
        peso_semana = 60 // PASO_MIN
        maximo_blando = (
            peso_semana * len(semanas) * len(self.problema.partidos)
            + (len(esperas) + len(temprano)) * self._pasos_por_dia
            + peso_semana * (len(dobles) + len(finales))
        )
        self.modelo.maximize(
            (1 + maximo_blando) * sum(self.presente.values())
            - peso_semana * sum(desvio)
            - sum(esperas)
            - sum(temprano)
            - peso_semana * (sum(dobles) + sum(finales))
        )

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
    modelo = Modelo(problema)
    modelo.variables()
    modelo.canchas()
    modelo.equipos()
    modelo.personas()
    modelo.orden()
    modelo.objetivo()
    return modelo.resolver(segundos, trabajadores, semilla)
