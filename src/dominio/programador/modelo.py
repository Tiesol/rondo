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
- orden (PRO-08, si la regla es "dura"): las fechas de cada equipo van en orden (P19). Con
  "blanda", cada par al revés cuesta en el objetivo (A2, fase 12);
- eliminación (PRO-09): después de la fase de grupos de su categoría y de los partidos a
  los que se refiere (sin ellos no se ubica). Su fin de semana (P33) es solo una sugerencia
  para repartir los grupos: semis y finales pueden ir antes (T11.4). Si toma posiciones de
  grupo y cae el mismo día que partidos de grupos, deja el turno libre (P17);
- fijos (PRO-10): los partidos empezados o jugados no se mueven. Pueden estar fuera de
  las franjas o con avisos que la organización confirmó al ponerlos a mano (T11.2): las
  restricciones entre dos fijos no se exigen, solo las de los que se mueven.

Objetivo: primero ubicar la mayor cantidad; después, cada fecha de grupos cerca de su fin de
semana, para repartir la carga (PRO-12), poca espera de los profes compartidos (PRO-11), los
chicos temprano (P56), un solo partido por día por equipo (P17), las finales en los dos últimos
días (P55) y los equipos de un club el mismo día (P20).
"""

import time
from collections import defaultdict
from collections.abc import Hashable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from itertools import combinations, pairwise

from ortools.sat.python import cp_model

from dominio.config import Reglas
from dominio.verificador import Bloqueo, FranjaExtra, ParDeEquipos

PASO_MIN = 5
Equipo = Hashable
# Un intervalo para no pisarse: el partido, su largo en pasos, si está activo y si es fijo.
type _Ocupa = tuple["PartidoAProgramar", int, cp_model.IntVar | int, bool]


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
    ronda: str = ""  # en la eliminación: "semi" o "final" (A1, fase 12)

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
    eliminacion_desde: datetime | None = None  # P33: sugerido, para repartir los grupos
    clubes: dict[Equipo, Hashable] = field(default_factory=dict)  # equipo → club (P20)
    extras: tuple[FranjaExtra, ...] = ()  # A4: tiempo agregado, solo si hace falta

    @property
    def todas_las_franjas(self) -> tuple[tuple[datetime, datetime], ...]:
        return self.franjas + tuple((e.desde, e.hasta) for e in self.extras)


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


def ronda_de(ronda: str, clave: str, id_: Hashable) -> str:
    """La ronda de una llave: la guardada o la que dice su clave ("oro_semi_1" es semi)."""
    if ronda:
        return ronda
    for nombre in ("final", "semi"):
        if nombre in clave:
            return nombre
    return str(id_)


def lugar_habitual(
    problema: Problema, partido: PartidoAProgramar, lugar: tuple[str, datetime]
) -> bool:
    """Si el programador podría haberlo puesto ahí: una cancha compatible, un día en que juega
    y dentro de una franja. Lo que se puso a mano en otro lado (T11.2) no se mueve solo."""
    cancha, inicio = lugar
    if cancha not in partido.canchas or inicio.weekday() in partido.dias_sin_jugar:
        return False
    ultimo_inicio = problema.reglas.fin_de_franja == "ultimo_inicio"
    fin = inicio if ultimo_inicio else inicio + timedelta(minutes=partido.minutos_partido)
    if any(desde <= inicio and fin <= hasta for desde, hasta in problema.franjas):
        return True
    return any(
        e.desde <= inicio and fin <= e.hasta and e.admite(cancha, problema.fisicas)
        for e in problema.extras
    )


def _pasos(minutos: int) -> int:
    return -(-minutos // PASO_MIN)  # hacia arriba


class Modelo:
    """El modelo CP-SAT armado por partes; programar() y reprogramar.proponer() lo usan."""

    def __init__(self, problema: Problema) -> None:
        self.problema = problema
        self.modelo = cp_model.CpModel()
        self.reloj = _Reloj(problema.todas_las_franjas)
        # Días de juego: la ventana de inicios posibles de cada día, en pasos.
        self.dias: dict[date, list[tuple[int, int]]] = defaultdict(list)
        for desde, hasta in problema.todas_las_franjas:
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
        # A2 (P19 "blanda"): pares de fechas seguidas de un equipo que quedaron al revés.
        self.al_reves: list[cp_model.IntVar] = []
        # A4 (P78): partidos ubicados en tiempo agregado; cuesta más que todo lo blando.
        self.en_extra: list[cp_model.IntVar] = []
        # Pares de partidos de equipos con un profe en común, y si el primero va antes (T7.3).
        self.profes_compartidos: list[
            tuple[PartidoAProgramar, PartidoAProgramar, cp_model.IntVar]
        ] = []

    def _ventana(
        self, partido: PartidoAProgramar, desde: datetime, hasta: datetime
    ) -> tuple[int, int] | None:
        # P48: el partido termina dentro de la franja, o solo empieza dentro (último inicio).
        if desde.weekday() in partido.dias_sin_jugar:
            return None  # P56: esa categoría no juega ese día
        ultimo_inicio = self.problema.reglas.fin_de_franja == "ultimo_inicio"
        largo = 0 if ultimo_inicio else _pasos(partido.minutos_partido)
        primero = self.reloj.paso(desde, hacia_arriba=True)
        ultimo = self.reloj.paso(hasta, hacia_arriba=False) - largo
        return (primero, ultimo) if ultimo >= primero else None

    def _inicios_posibles(self, partido: PartidoAProgramar) -> list[tuple[int, int]]:
        ventanas = [self._ventana(partido, desde, hasta) for desde, hasta in self.problema.franjas]
        return [v for v in ventanas if v is not None]

    def _extras_posibles(
        self, partido: PartidoAProgramar
    ) -> list[tuple[FranjaExtra, tuple[int, int]]]:
        """El tiempo agregado donde podría ir: en el día y en alguna de sus canchas."""
        posibles = []
        for extra in self.problema.extras:
            ventana = self._ventana(partido, extra.desde, extra.hasta)
            canchas = partido.canchas & set(self.problema.fisicas)
            if ventana and any(extra.admite(c, self.problema.fisicas) for c in canchas):
                posibles.append((extra, ventana))
        return posibles

    def _dominio(self, partido: PartidoAProgramar) -> cp_model.Domain:
        """Los inicios posibles: dentro de las franjas (o del tiempo agregado) y fuera de los
        bloqueos de sus equipos."""
        ventanas = self._inicios_posibles(partido) + [v for _, v in self._extras_posibles(partido)]
        dominio = cp_model.Domain.from_intervals([list(v) for v in ventanas])
        largo = _pasos(partido.minutos_partido)
        for bloqueo in self.problema.bloqueos:
            if bloqueo.equipo in partido.equipos_definidos:
                desde = self.reloj.paso(bloqueo.inicio, hacia_arriba=False) - largo + 1
                hasta = self.reloj.paso(bloqueo.fin, hacia_arriba=True) - 1
                dominio = dominio.intersection_with(cp_model.Domain(desde, hasta).complement())
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

            if not partido.fijo:
                self._tiempo_extra(partido)

            if partido.fijo:  # T11.2: puede estar fuera de las franjas de su día
                dia_fijo = partido.fijo[1].date()
                self.en_dia[partido.id] = {
                    dia: m.new_constant(int(dia == dia_fijo)) for dia in self.dias
                }
            else:
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
                else:  # en una cancha que no es compatible (T11.2): se respeta igual
                    self.en_cancha[partido.id][cancha] = m.new_constant(1)

    def _tiempo_extra(self, partido: PartidoAProgramar) -> None:
        """A4 (P78): si va en tiempo agregado, solo en las canchas de ese tiempo; si no, en el
        horario normal. Cada partido en tiempo agregado cuesta en el objetivo."""
        extras = self._extras_posibles(partido)
        if not extras:
            return
        m = self.modelo
        inicio, presente = self.inicio[partido.id], self.presente[partido.id]
        en_extra = m.new_bool_var(f"{partido.id} en tiempo agregado")
        usa = []
        for i, (extra, (primero, ultimo)) in enumerate(extras):
            aca = m.new_bool_var(f"{partido.id} en el agregado {i}")
            m.add(inicio >= primero).only_enforce_if(aca)
            m.add(inicio <= ultimo).only_enforce_if(aca)
            for cancha, elegida in self.en_cancha[partido.id].items():
                if not extra.admite(cancha, self.problema.fisicas):
                    m.add_implication(aca, elegida.Not())
            usa.append(aca)
        m.add(sum(usa) == en_extra)
        m.add_implication(en_extra, presente)
        normal = cp_model.Domain.from_intervals([list(v) for v in self._inicios_posibles(partido)])
        m.add_linear_expression_in_domain(inicio, normal).only_enforce_if(
            [presente, en_extra.Not()]
        )
        self.en_extra.append(en_extra)

    def _paso_fijo(self, partido: PartidoAProgramar) -> int:
        assert partido.fijo is not None
        return self.reloj.paso(partido.fijo[1], hacia_arriba=False)

    def _sin_pisarse(self, ocupan: list[_Ocupa], nombre: str) -> None:
        """Que no se pisen. Si dos fijos ya se pisan (un aviso confirmado al moverlos a mano,
        T11.2), se comparan solo los pares con algo que se mueve: si no, no habría solución."""

        def intervalo(ocupa: _Ocupa) -> cp_model.IntervalVar:
            partido, largo, activo, _ = ocupa
            return self.modelo.new_optional_fixed_size_interval_var(
                self.inicio[partido.id], largo, activo, f"{nombre} {partido.id}"
            )

        fijos = [(self._paso_fijo(p), largo) for p, largo, _, fijo in ocupan if fijo]
        if not any(a < b + lb and b < a + la for (a, la), (b, lb) in combinations(fijos, 2)):
            self.modelo.add_no_overlap([intervalo(o) for o in ocupan])
            return
        for uno, otro in combinations(ocupan, 2):
            if not (uno[3] and otro[3]):
                self.modelo.add_no_overlap([intervalo(uno), intervalo(otro)])

    def canchas(self) -> None:
        por_unidad: dict[str, list[_Ocupa]] = defaultdict(list)
        for partido in self.problema.partidos:
            turno = _pasos(partido.minutos_turno)
            for cancha, elegida in self.en_cancha[partido.id].items():
                if partido.fijo and partido.fijo[0] != cancha:
                    continue  # un fijo está solo en su cancha
                for unidad in self.problema.fisicas.get(cancha, frozenset({cancha})):
                    por_unidad[unidad].append((partido, turno, elegida, partido.fijo is not None))
        for unidad, ocupan in por_unidad.items():
            self._sin_pisarse(ocupan, f"ocupa {unidad}")

    def equipos(self) -> None:
        reglas = self.problema.reglas
        por_equipo: dict[Equipo, list[PartidoAProgramar]] = defaultdict(list)
        for partido in self.problema.partidos:
            for equipo in partido.equipos_y_virtuales:
                por_equipo[equipo].append(partido)
        for suyos in por_equipo.values():
            # El turno más los turnos libres del día (P17): de un día al siguiente sobra lugar.
            self._sin_pisarse(
                [
                    (
                        p,
                        _pasos(p.minutos_turno) * (1 + reglas.turnos_libres_mismo_dia),
                        self.presente[p.id],
                        p.fijo is not None,
                    )
                    for p in suyos
                ],
                "equipo en",
            )
            for dia in self.dias:
                # Si los fijos ya pasan del máximo (un aviso confirmado), no se suma ninguno.
                fijos = sum(1 for p in suyos if p.fijo and p.fijo[1].date() == dia)
                self.modelo.add(
                    sum(self.en_dia[p.id][dia] for p in suyos)
                    <= max(reglas.max_partidos_por_dia, fijos)
                )

    def grupos_y_llaves_por_dia(self) -> None:
        """A1 (P47): un equipo que juega grupos un día no puede, además, poder jugar ese día
        tantas rondas de eliminación de su categoría que pase del máximo. Cada ronda (semi,
        final) cuenta uno si alguna de sus llaves cae ese día y el equipo podría jugarla."""
        maximo = self.problema.reglas.max_partidos_por_dia
        grupos: dict[str, list[PartidoAProgramar]] = defaultdict(list)
        llaves: dict[str, list[PartidoAProgramar]] = defaultdict(list)
        for partido in self.problema.partidos:
            (grupos if partido.fase == "grupos" else llaves)[partido.categoria].append(partido)
        m = self.modelo
        for categoria, suyas in llaves.items():
            de_grupos = grupos.get(categoria, [])
            if not de_grupos:
                continue
            for dia in self.dias:
                for equipo in {e for g in de_grupos for e in g.equipos_definidos}:
                    por_ronda: dict[str, list[PartidoAProgramar]] = defaultdict(list)
                    for llave in suyas:
                        if None in llave.equipos or equipo in llave.equipos:
                            por_ronda[ronda_de(llave.ronda, llave.clave, llave.id)].append(llave)
                    if not por_ronda:
                        continue
                    hay = []
                    for ronda, de_la_ronda in por_ronda.items():
                        variable = m.new_bool_var(f"{categoria} {ronda} el {dia} para {equipo}")
                        m.add_max_equality(variable, [self.en_dia[p.id][dia] for p in de_la_ronda])
                        hay.append(variable)
                    suyos = [g for g in de_grupos if equipo in g.equipos_definidos]
                    fijos = sum(1 for g in suyos if g.fijo and g.fijo[1].date() == dia) + sum(
                        1
                        for de_la_ronda in por_ronda.values()
                        if any(p.fijo and p.fijo[1].date() == dia for p in de_la_ronda)
                    )
                    m.add(
                        sum(self.en_dia[g.id][dia] for g in suyos) + sum(hay) <= max(maximo, fijos)
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
            self._sin_pisarse(
                [
                    (p, _pasos(p.minutos_partido), self.presente[p.id], p.fijo is not None)
                    for p in juntos.values()
                ],
                f"{par.motivo} en",
            )
            if par.motivo != "profe":
                continue
            for uno in por_equipo.get(par.a, []):
                for otro in por_equipo.get(par.b, []):
                    clave = (uno.id, otro.id) if str(uno.id) <= str(otro.id) else (otro.id, uno.id)
                    if uno.fijo and otro.fijo:
                        continue  # T11.2: ya están puestos; no se exige nada entre ellos
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

    def _dias_por_club(self) -> list[cp_model.IntVar]:
        """P20: de preferencia, los equipos de un club juegan el mismo día. Uno por club y día
        en que juega alguno de sus equipos: menos días es mejor."""
        por_club: dict[Hashable, dict[Hashable, PartidoAProgramar]] = defaultdict(dict)
        for partido in self.problema.partidos:
            for equipo in partido.equipos_definidos:
                if equipo in self.problema.clubes:
                    por_club[self.problema.clubes[equipo]][partido.id] = partido
        dias = []
        for club, suyos in por_club.items():
            equipos = {e for p in suyos.values() for e in p.equipos_definidos}
            if len({e for e in equipos if self.problema.clubes.get(e) == club}) < 2:
                continue  # con un solo equipo no hay nada que juntar
            for dia in self.dias:
                juega = self.modelo.new_bool_var(f"{club} juega el {dia}")
                self.modelo.add_max_equality(juega, [self.en_dia[i][dia] for i in suyos])
                dias.append(juega)
        return dias

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
        if antes.fijo and despues.fijo:
            return  # T11.2: ya están puestos; si el orden quedó al revés, es un aviso
        ambos = [self.presente[antes.id], self.presente[despues.id]]
        turno = _pasos(antes.minutos_turno)
        self.modelo.add(self.inicio[despues.id] >= self.inicio[antes.id] + turno).only_enforce_if(
            ambos
        )
        if not descanso:
            return
        libres = self.problema.reglas.turnos_libres_mismo_dia
        for dia in self.dias:
            self.modelo.add(
                self.inicio[despues.id] >= self.inicio[antes.id] + turno * (1 + libres)
            ).only_enforce_if([*ambos, self.en_dia[antes.id][dia], self.en_dia[despues.id][dia]])

    def orden(self) -> None:
        partidos = self.problema.partidos
        dura = self.problema.reglas.orden_de_fechas == "dura"
        por_equipo: dict[Equipo, list[PartidoAProgramar]] = defaultdict(list)
        for partido in partidos:
            if partido.fase == "grupos" and partido.fecha is not None:
                for equipo in partido.equipos_definidos:
                    por_equipo[equipo].append(partido)
        for equipo, suyos in por_equipo.items():
            suyos.sort(key=lambda p: p.fecha or 0)
            for antes, despues in pairwise(suyos):
                if (antes.fecha or 0) >= (despues.fecha or 0):
                    continue
                if dura:
                    self._despues(antes, despues)
                elif not (antes.fijo and despues.fijo):
                    # A2 (P19 "blanda"): se permite al revés, pero cuesta en el objetivo.
                    reves = self.modelo.new_bool_var(f"{equipo}: {despues.id} antes que {antes.id}")
                    turno = _pasos(antes.minutos_turno)
                    self.modelo.add(
                        self.inicio[despues.id] >= self.inicio[antes.id] + turno
                    ).only_enforce_if(
                        [self.presente[antes.id], self.presente[despues.id], reves.Not()]
                    )
                    self.al_reves.append(reves)

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
                if not llave.fijo:
                    self.modelo.add_implication(self.presente[llave.id], self.presente[anterior.id])

    def objetivo(self) -> None:
        """Ubicar manda siempre. Después, que cada fecha caiga cerca de su fin de semana
        (PRO-12) y que los profes compartidos esperen poco entre sus partidos (PRO-11): una
        semana de desvío pesa como una hora de espera."""
        semanas = sorted({dia.isocalendar()[:2] for dia in self.dias})
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
        clubes = self._dias_por_club()
        peso_semana = 60 // PASO_MIN
        peso_reves = 4 * peso_semana  # A2: cuando se puede, ninguna fecha al revés
        maximo_blando = (
            peso_semana * len(semanas) * len(self.problema.partidos)
            + (len(esperas) + len(temprano)) * self._pasos_por_dia
            + peso_semana * (len(dobles) + len(finales) + len(clubes))
            + peso_reves * len(self.al_reves)
        )
        # A4: el tiempo agregado se usa solo si sin él algo queda afuera: ubicar pesa más que
        # todo el tiempo agregado, y el tiempo agregado más que todo lo demás.
        peso_extra = 1 + maximo_blando
        maximo_blando += peso_extra * len(self.en_extra)
        self.modelo.maximize(
            (1 + maximo_blando) * sum(self.presente.values())
            - peso_semana * sum(desvio)
            - sum(esperas)
            - sum(temprano)
            - peso_semana * (sum(dobles) + sum(finales) + sum(clubes))
            - peso_reves * sum(self.al_reves)
            - peso_extra * sum(self.en_extra)
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
    modelo.grupos_y_llaves_por_dia()
    modelo.personas()
    modelo.orden()
    modelo.objetivo()
    return modelo.resolver(segundos, trabajadores, semilla)
