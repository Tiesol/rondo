"""Cruces de la eliminación desde la tabla (T8.8, P50).

Con la fase de grupos terminada, la app propone los equipos de cada llave sin asignar: las
posiciones salen de la tabla (1.º A, mejor 3.º según P26); el ganador o el perdedor, de la
llave ya jugada; el mejor perdedor, por P26. La propuesta se verifica con el calendario antes
de guardarla, y se puede corregir a mano (T6.1).
"""

from dataclasses import dataclass, field

from django.db import transaction

from dominio.config import Reglas
from dominio.formatos import FormatoFaltante, Participante
from dominio.tabla import Fila, mejores
from torneo.models import CategoriaNivel, Equipo, Partido
from torneo.servicios.fixture import formato_para
from torneo.servicios.partido import resultado_de
from torneo.servicios.programador import (
    calendario_actual,
    choques_del_calendario,
    partidos_del_torneo,
    problema_del_torneo,
)
from torneo.servicios.tabla import TablaDeSerie, tablas_de

Cruce = tuple[Equipo, Equipo]


@dataclass
class Propuesta:
    cruces: list[tuple[Partido, Cruce]] = field(default_factory=list)
    problema: str = ""  # por qué no se propone nada todavía
    choques: list[str] = field(default_factory=list)  # con estos equipos, el calendario choca


class _Pendiente(Exception):
    """Ese participante todavía no se conoce (su llave no se jugó)."""


def _plural(n: int, uno: str, varios: str) -> str:
    return f"{n} {uno if n == 1 else varios}"


def _problema_de_grupos(categoria: CategoriaNivel, tablas: list[TablaDeSerie]) -> str:
    faltan = categoria.partidos.filter(fase=Partido.Fase.GRUPOS).exclude(
        estado=Partido.Estado.JUGADO
    )
    if (cantidad := faltan.count()) > 0:
        return f"Falta jugar {_plural(cantidad, 'partido de grupos', 'partidos de grupos')}."
    sin_sortear = [e.nombre for t in tablas for e in t.falta_sorteo]
    if sin_sortear:
        return f"Falta registrar el sorteo de {', '.join(sin_sortear)} (P28), en Posiciones."
    return ""


class _Resolver:
    def __init__(self, categoria: CategoriaNivel, tablas: list[TablaDeSerie]) -> None:
        self.por_serie = {t.nombre: t for t in tablas}
        self.equipos = {pk: e for t in tablas for pk, e in t.equipos.items()}
        self.filas = {f.equipo: f for t in tablas for f in t.filas}
        self.llaves = {p.clave: p for p in categoria.partidos.filter(fase="eliminacion")}

    def _en_puesto(self, serie: str, puesto: int) -> Fila:
        return self.por_serie[serie].filas[puesto - 1]

    def _resultado(self, clave: str) -> tuple[Equipo, Equipo]:
        """(ganador, perdedor) de una llave jugada."""
        llave = self.llaves.get(clave)
        if llave is None or llave.estado != Partido.Estado.JUGADO:
            raise _Pendiente
        assert llave.local is not None and llave.visitante is not None
        ganador = resultado_de(llave).ganador
        if ganador == "local":
            return llave.local, llave.visitante
        return llave.visitante, llave.local

    def equipo(self, participante: Participante) -> Equipo:
        if participante.puesto is not None:
            serie = participante.serie or next(iter(self.por_serie))
            return self.equipos[self._en_puesto(serie, participante.puesto).equipo]
        if participante.mejor_puesto is not None or participante.otro_puesto is not None:
            puesto = participante.mejor_puesto or participante.otro_puesto or 0
            orden = mejores([self._en_puesto(s, puesto) for s in self.por_serie])
            elegido = orden[0] if participante.mejor_puesto is not None else orden[1]
            return self.equipos[elegido.equipo]
        if participante.ganador:
            return self._resultado(participante.ganador)[0]
        if participante.perdedor:
            return self._resultado(participante.perdedor)[1]
        perdedores = [self._resultado(clave)[1] for clave in participante.mejor_perdedor]
        mejor = mejores([self.filas[e.pk] for e in perdedores])[0]
        return self.equipos[mejor.equipo]


def proponer(categoria: CategoriaNivel) -> Propuesta:
    reglas = Reglas.model_validate(categoria.torneo.reglas)
    try:
        formato = formato_para(reglas, categoria.equipos.count())
    except FormatoFaltante as error:
        return Propuesta(problema=str(error))
    tablas = tablas_de(categoria)
    problema = _problema_de_grupos(categoria, tablas)
    if problema:
        return Propuesta(problema=problema)
    resolver = _Resolver(categoria, tablas)
    propuesta = Propuesta()
    for llave in formato.eliminacion:
        partido = resolver.llaves.get(llave.clave)
        if partido is None or partido.local_id or partido.visitante_id:
            continue  # ya asignada (a mano o antes): no se toca
        try:
            cruce = (
                resolver.equipo(llave.local.participante),
                resolver.equipo(llave.visitante.participante),
            )
        except _Pendiente:
            continue
        propuesta.cruces.append((partido, cruce))
    propuesta.choques = _choques(categoria, propuesta)
    return propuesta


def _choques(categoria: CategoriaNivel, propuesta: Propuesta) -> list[str]:
    """Los choques del calendario si se asignan estos equipos, sin guardar nada."""
    if not propuesta.cruces:
        return []
    asignados = {p.pk: cruce for p, cruce in propuesta.cruces}
    partidos = partidos_del_torneo(categoria.torneo)
    for partido in partidos:
        if partido.pk in asignados:
            partido.local, partido.visitante = asignados[partido.pk]
    calendario = choques_del_calendario(
        problema_del_torneo(categoria.torneo, partidos), calendario_actual(partidos)
    )
    return [m for c in calendario if set(c.partidos) & set(asignados) for m in c.motivos]


@transaction.atomic
def aplicar(categoria: CategoriaNivel, propuesta: Propuesta) -> int:
    for partido, (local, visitante) in propuesta.cruces:
        partido.local, partido.visitante = local, visitante
        partido.save(update_fields=["local", "visitante"])
    return len(propuesta.cruces)
