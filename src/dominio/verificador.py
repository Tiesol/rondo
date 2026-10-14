"""Verificador de choques (VER-01; PRO-01 a PRO-07): recibe cualquier calendario.

Sirve para el calendario que arma el programador, para uno hecho a mano (la prueba de 2023)
y para revisar un cambio manual. Un choque es un par de partidos (o un partido solo, si es de
compatibilidad, de franja o de bloqueo) con la lista de sus motivos, y un tipo:

- cancha: dos partidos usan la misma cancha física a la vez (C1 entera ocupa C1A y C1B);
- compatibilidad: la categoría no juega en esa cancha;
- franja: el partido no empieza y termina dentro de una franja (el cambio puede quedar
  afuera, P48);
- equipo: un equipo juega dos partidos que se pisan, no deja los turnos libres del día (P17)
  o pasa del máximo de partidos por día (P47). En la eliminación cuentan los equipos
  virtuales (el ganador de una semi juega la final) y el descanso entre los partidos de
  grupos y la llave que toma sus posiciones, si caen el mismo día (T7.1);
- persona: dos equipos que comparten un jugador juegan a la vez (P36), o que comparten un
  profe juegan a la vez o en canchas distintas sin el margen para cambiar (P18, P35);
- bloqueo: un equipo juega durante un bloqueo de la ACF.

Un par de partidos con varios motivos del mismo tipo cuenta como un solo choque (H1).

T11.2 (Rondo propone y avisa; la organización decide): un choque **bloquea** solo si es
físicamente imposible, es decir dos partidos a la vez en la misma cancha física o un equipo
en dos partidos a la vez. Todo lo demás es un aviso que se puede confirmar.
"""

from collections import defaultdict
from collections.abc import Callable, Hashable, Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from itertools import combinations
from typing import Literal

from dominio.config import Reglas

TipoDeChoque = Literal["cancha", "compatibilidad", "franja", "equipo", "persona", "bloqueo"]
Equipo = Hashable
type _Anotar = Callable[..., None]


@dataclass(frozen=True)
class PartidoAgendado:
    id: Hashable
    categoria: str  # la clave de compatibilidad, como "Sub 9|inicial"
    equipos: tuple[Equipo | None, Equipo | None]  # None mientras esté por definir
    cancha: str
    inicio: datetime
    minutos_partido: int  # dos tiempos y el descanso
    minutos_turno: int  # más el cambio entre partidos
    fase: str = "grupos"  # o "eliminacion"
    virtuales: frozenset[str] = frozenset()  # en la eliminación: "ganador de la semi 1" (T7.1)
    toma_posiciones: bool = False  # en la eliminación: juega con equipos de la tabla de grupos
    dias_sin_jugar: frozenset[int] = frozenset()  # días de la semana (0 es lunes), P56
    ronda: str = ""  # en la eliminación: "semi" o "final" (A1, fase 12)

    @property
    def fin_partido(self) -> datetime:
        return self.inicio + timedelta(minutes=self.minutos_partido)

    @property
    def fin_turno(self) -> datetime:
        return self.inicio + timedelta(minutes=self.minutos_turno)

    @property
    def dia(self) -> date:
        return self.inicio.date()

    @property
    def equipos_definidos(self) -> tuple[Equipo, ...]:
        return tuple(e for e in self.equipos if e is not None)

    @property
    def equipos_y_virtuales(self) -> tuple[Equipo, ...]:
        """Para las reglas de equipo (P17, P47): los definidos y los virtuales de las llaves."""
        return self.equipos_definidos + tuple(sorted(self.virtuales))


@dataclass(frozen=True)
class ParDeEquipos:
    """Dos equipos que comparten una persona. Se calcula desde Persona (ARQUITECTURA 6)."""

    a: Equipo
    b: Equipo
    motivo: Literal["profe", "jugador"]


@dataclass(frozen=True)
class Bloqueo:
    equipo: Equipo
    inicio: datetime
    fin: datetime
    motivo: str = "partido de la ACF"


@dataclass(frozen=True)
class Escenario:
    fisicas: dict[str, frozenset[str]]  # cancha → canchas físicas que ocupa
    compatibilidad: dict[str, frozenset[str]]  # categoría → canchas donde puede jugar
    franjas: tuple[tuple[datetime, datetime], ...]
    pares: tuple[ParDeEquipos, ...]
    bloqueos: tuple[Bloqueo, ...]
    reglas: Reglas


@dataclass(frozen=True)
class Choque:
    tipo: TipoDeChoque
    partidos: tuple[Hashable, ...]
    motivos: tuple[str, ...] = field(default=())
    bloquea: bool = False  # T11.2: físicamente imposible; si no, es un aviso


def _se_pisan(inicio_a: datetime, fin_a: datetime, inicio_b: datetime, fin_b: datetime) -> bool:
    return inicio_a < fin_b and inicio_b < fin_a


def _minutos_entre(primero: PartidoAgendado, segundo: PartidoAgendado) -> float:
    """Del final del partido que empieza antes al inicio del otro (negativo si se pisan)."""
    antes, despues = sorted((primero, segundo), key=lambda p: p.inicio)
    return (despues.inicio - antes.fin_partido).total_seconds() / 60


def verificar(partidos: Iterable[PartidoAgendado], escenario: Escenario) -> list[Choque]:
    lista = sorted(partidos, key=lambda p: (p.inicio, str(p.id)))
    motivos: dict[tuple[TipoDeChoque, tuple[Hashable, ...]], list[str]] = defaultdict(list)
    bloquean: set[tuple[TipoDeChoque, tuple[Hashable, ...]]] = set()

    def anotar(
        tipo: TipoDeChoque, ids: Iterable[Hashable], motivo: str, *, bloquea: bool = False
    ) -> None:
        clave = (tipo, tuple(ids))
        motivos[clave].append(motivo)
        if bloquea:
            bloquean.add(clave)

    for partido in lista:
        _uno_solo(partido, escenario, anotar)
    for uno, otro in combinations(lista, 2):
        _cancha(uno, otro, escenario, anotar)
    _equipos(lista, escenario.reglas, anotar)
    _grupos_y_llaves(lista, escenario.reglas, anotar)
    _maximo_con_llaves(lista, escenario.reglas, anotar)
    _personas(lista, escenario, anotar)

    return [
        Choque(tipo, ids, tuple(lista_), (tipo, ids) in bloquean)
        for (tipo, ids), lista_ in motivos.items()
    ]


def _uno_solo(partido: PartidoAgendado, escenario: Escenario, anotar: _Anotar) -> None:
    compatibles = escenario.compatibilidad.get(partido.categoria, frozenset())
    if partido.cancha not in compatibles:
        anotar(
            "compatibilidad",
            (partido.id,),
            f"{partido.categoria} no juega en {partido.cancha}",
        )
    ultimo_inicio = escenario.reglas.fin_de_franja == "ultimo_inicio"  # P48
    if not any(
        desde <= partido.inicio
        and (partido.inicio if ultimo_inicio else partido.fin_partido) <= hasta
        for desde, hasta in escenario.franjas
    ):
        anotar("franja", (partido.id,), "Fuera de las franjas de juego")
    if partido.inicio.weekday() in partido.dias_sin_jugar:
        anotar("franja", (partido.id,), f"{partido.categoria} no juega ese día de la semana (P56)")
    for bloqueo in escenario.bloqueos:
        if bloqueo.equipo in partido.equipos_definidos and _se_pisan(
            partido.inicio, partido.fin_partido, bloqueo.inicio, bloqueo.fin
        ):
            anotar("bloqueo", (partido.id,), f"{bloqueo.equipo}: {bloqueo.motivo}")


def _cancha(
    uno: PartidoAgendado, otro: PartidoAgendado, escenario: Escenario, anotar: _Anotar
) -> None:
    comunes = escenario.fisicas.get(uno.cancha, frozenset({uno.cancha})) & escenario.fisicas.get(
        otro.cancha, frozenset({otro.cancha})
    )
    if not comunes:
        return
    donde = ", ".join(sorted(comunes))
    if _se_pisan(uno.inicio, uno.fin_partido, otro.inicio, otro.fin_partido):
        anotar("cancha", (uno.id, otro.id), f"Se pisan en {donde}", bloquea=True)
    elif _se_pisan(uno.inicio, uno.fin_turno, otro.inicio, otro.fin_turno):
        anotar("cancha", (uno.id, otro.id), f"Sin el tiempo de cambio en {donde}")


def _equipos(lista: list[PartidoAgendado], reglas: Reglas, anotar: _Anotar) -> None:
    por_equipo: dict[Equipo, list[PartidoAgendado]] = defaultdict(list)
    for partido in lista:
        for equipo in partido.equipos_y_virtuales:
            por_equipo[equipo].append(partido)
    for equipo, suyos in por_equipo.items():
        por_dia: dict[date, list[PartidoAgendado]] = defaultdict(list)
        for partido in suyos:
            por_dia[partido.dia].append(partido)
        for del_dia in por_dia.values():
            if len(del_dia) > reglas.max_partidos_por_dia:
                anotar(
                    "equipo",
                    (p.id for p in del_dia),
                    f"{equipo}: {len(del_dia)} partidos en el día "
                    f"(máximo {reglas.max_partidos_por_dia})",
                )
            for uno, otro in combinations(del_dia, 2):
                if _se_pisan(uno.inicio, uno.fin_partido, otro.inicio, otro.fin_partido):
                    anotar(
                        "equipo",
                        (uno.id, otro.id),
                        f"{equipo}: juega dos partidos a la vez",
                        bloquea=True,
                    )
                    continue
                libre = (otro.inicio - uno.fin_turno).total_seconds() / 60
                if libre < reglas.turnos_libres_mismo_dia * uno.minutos_turno:
                    anotar(
                        "equipo",
                        (uno.id, otro.id),
                        f"{equipo}: sin {reglas.turnos_libres_mismo_dia} turno libre entre "
                        "sus partidos del día",
                    )


def _grupos_y_llaves(lista: list[PartidoAgendado], reglas: Reglas, anotar: _Anotar) -> None:
    """Una llave que toma posiciones de grupo, el mismo día que partidos de grupos de su
    categoría: cualquiera de esos equipos puede jugarla, así que deja el turno libre (P17)."""
    grupos: dict[tuple[str, date], list[PartidoAgendado]] = defaultdict(list)
    for partido in lista:
        if partido.fase == "grupos":
            grupos[(partido.categoria, partido.dia)].append(partido)
    for llave in lista:
        if not llave.toma_posiciones:
            continue
        for grupo in grupos.get((llave.categoria, llave.dia), []):
            if grupo.inicio > llave.inicio:
                continue  # eso lo ve el orden de la eliminación, no el descanso
            libre = (llave.inicio - grupo.fin_turno).total_seconds() / 60
            if libre < reglas.turnos_libres_mismo_dia * grupo.minutos_turno:
                anotar(
                    "equipo",
                    (grupo.id, llave.id),
                    f"Sin {reglas.turnos_libres_mismo_dia} turno libre entre la fase de grupos "
                    "y la llave que toma sus posiciones",
                )


def _rondas_que_puede_jugar(equipo: Equipo, llaves: list[PartidoAgendado]) -> set[str]:
    """Las rondas de eliminación de ese día que el equipo podría jugar: las llaves por definir
    pueden ser de cualquiera; las ya asignadas, solo de sus dos equipos."""
    return {
        llave.ronda or str(llave.id)
        for llave in llaves
        if None in llave.equipos or equipo in llave.equipos
    }


def _maximo_con_llaves(lista: list[PartidoAgendado], reglas: Reglas, anotar: _Anotar) -> None:
    """A1 (P47): un equipo que juega grupos un día puede jugar después ese mismo día la semi
    y la final de su categoría. Se cuenta un partido por ronda que podría jugar."""
    grupos: dict[tuple[str, date], list[PartidoAgendado]] = defaultdict(list)
    llaves: dict[tuple[str, date], list[PartidoAgendado]] = defaultdict(list)
    for partido in lista:
        destino = grupos if partido.fase == "grupos" else llaves
        destino[(partido.categoria, partido.dia)].append(partido)
    for clave, del_dia in llaves.items():
        de_grupos = grupos.get(clave, [])
        for equipo in {e for g in de_grupos for e in g.equipos_definidos}:
            suyos = [g for g in de_grupos if equipo in g.equipos_definidos]
            rondas = _rondas_que_puede_jugar(equipo, del_dia)
            if len(suyos) + len(rondas) > reglas.max_partidos_por_dia:
                anotar(
                    "equipo",
                    (p.id for p in suyos + del_dia),
                    f"{equipo}: puede jugar {len(suyos) + len(rondas)} partidos el día, con "
                    f"grupos y eliminación (máximo {reglas.max_partidos_por_dia})",
                )


def _personas(lista: list[PartidoAgendado], escenario: Escenario, anotar: _Anotar) -> None:
    por_equipo: dict[Equipo, list[PartidoAgendado]] = defaultdict(list)
    for partido in lista:
        for equipo in partido.equipos_definidos:
            por_equipo[equipo].append(partido)
    margen = escenario.reglas.profe_minutos_cambio_de_cancha
    for par in escenario.pares:
        for uno in por_equipo.get(par.a, []):
            for otro in por_equipo.get(par.b, []):
                if uno.id == otro.id or uno.dia != otro.dia:
                    continue
                separacion = _minutos_entre(uno, otro)
                if separacion < 0:
                    problema = "juegan a la vez"
                elif par.motivo == "profe" and uno.cancha != otro.cancha and separacion < margen:
                    problema = f"{separacion:.0f} min para cambiar de cancha (mínimo {margen})"
                else:
                    continue
                ids = tuple(p.id for p in sorted((uno, otro), key=lambda p: (p.inicio, str(p.id))))
                anotar("persona", ids, f"{par.motivo}: {par.a} y {par.b} {problema}")
