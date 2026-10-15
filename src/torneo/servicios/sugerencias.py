"""Horarios libres sugeridos al mover un partido (T13.17), sin solver.

Recorre los inicios posibles (cada franja del torneo en cada cancha compatible con la
categoría), del más cercano al horario actual al más lejano. Primero descarta rápido lo
físicamente imposible (la cancha o un equipo ocupados a esa hora); a los que quedan los pasa por
el mismo verificador que Mover e Intercambiar. Devuelve los que no tienen ningún aviso y,
aparte, los que solo tienen avisos, con el motivo.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from django.utils import timezone

from dominio.config import Reglas
from torneo.models import Cancha, Partido
from torneo.servicios.programador import (
    choques_del_calendario,
    hora_local,
    partidos_del_torneo,
    problema_del_torneo,
)

PASO = timedelta(minutes=5)  # como el programador


@dataclass
class Sugerencia:
    cancha: Cancha
    inicio: datetime
    avisos: list[str]


def _se_pisan(a: Cancha, b: Cancha) -> bool:
    """La misma cancha, o una entera y su mitad (las dos mitades sí conviven)."""
    return a.pk == b.pk or a.padre_id == b.pk or b.padre_id == a.pk


def _candidatos(partido: Partido, ahora: datetime) -> list[tuple[Cancha, datetime]]:
    torneo = partido.categoria.torneo
    reglas = Reglas.model_validate(torneo.reglas)
    compatibles = list(partido.categoria.canchas.select_related("padre"))
    duracion = timedelta(minutes=partido.categoria.minutos_partido)
    candidatos = []
    for franja in torneo.franjas.filter(suspendida=False).prefetch_related("canchas"):
        donde = {c.pk for c in franja.canchas.all()}
        ultimo = franja.fin if reglas.fin_de_franja == "ultimo_inicio" else franja.fin - duracion
        for cancha in compatibles:
            entera = cancha.padre_id or cancha.pk
            if donde and cancha.pk not in donde and entera not in donde:
                continue
            inicio = franja.inicio
            while inicio <= ultimo:
                if inicio >= ahora:
                    candidatos.append((cancha, inicio))
                inicio += PASO
    return candidatos


def horarios_libres(
    partido: Partido, *, cuantos: int = 8, con_avisos: int = 5, ahora: datetime | None = None
) -> tuple[list[Sugerencia], list[Sugerencia]]:
    """Hasta `cuantos` horarios sin ningún choque ni aviso y hasta `con_avisos` que solo tienen
    avisos, del más cercano al horario actual al más lejano."""
    ahora = ahora or timezone.now()
    torneo = partido.categoria.torneo
    partidos = [p for p in partidos_del_torneo(torneo) if p.pk != partido.pk]
    turno = timedelta(minutes=partido.categoria.minutos_turno)
    equipos = {e for e in (partido.local_id, partido.visitante_id) if e is not None}

    # Lo ocupado, por día: (cancha, inicio, fin) y lo de los equipos del partido.
    por_dia: dict[date, list[Partido]] = defaultdict(list)
    for p in partidos:
        if p.inicio is not None and p.cancha is not None:
            por_dia[timezone.localtime(p.inicio).date()].append(p)

    def fin(p: Partido) -> datetime:
        assert p.inicio is not None
        return p.inicio + timedelta(minutes=p.categoria.minutos_turno)

    def libre(cancha: Cancha, inicio: datetime) -> bool:
        termina = inicio + turno
        for p in por_dia[timezone.localtime(inicio).date()]:
            assert p.inicio is not None and p.cancha is not None
            if p.inicio >= termina or fin(p) <= inicio:
                continue
            if _se_pisan(p.cancha, cancha) or {p.local_id, p.visitante_id} & equipos:
                return False
        return True

    referencia = partido.inicio or ahora

    def cercania(candidato: tuple[Cancha, datetime]) -> tuple[int, int, float, str]:
        cancha, inicio = candidato
        otro_dia = timezone.localtime(inicio).date() != timezone.localtime(referencia).date()
        otra_semana = (
            timezone.localtime(inicio).isocalendar()[:2]
            != timezone.localtime(referencia).isocalendar()[:2]
        )
        distancia = abs((inicio - referencia).total_seconds())
        return (otro_dia, otra_semana, distancia, cancha.codigo)

    problema = problema_del_torneo(torneo, [*partidos, partido])
    libres: list[Sugerencia] = []
    avisados: list[Sugerencia] = []
    for cancha, inicio in sorted(_candidatos(partido, ahora), key=cercania):
        if len(libres) >= cuantos and len(avisados) >= con_avisos:
            break
        if (cancha.pk, inicio) == (partido.cancha_id, partido.inicio) or not libre(cancha, inicio):
            continue
        avisos = _avisos(problema, partido, cancha, inicio, partidos, equipos)
        if avisos is None:  # lo bloquea el verificador
            continue
        if not avisos and len(libres) < cuantos:
            libres.append(Sugerencia(cancha, inicio, []))
        elif avisos and len(avisados) < con_avisos:
            avisados.append(Sugerencia(cancha, inicio, avisos))
    return libres, avisados


def _avisos(
    problema: Any,
    partido: Partido,
    cancha: Cancha,
    inicio: datetime,
    partidos: list[Partido],
    equipos: set[int],
) -> list[str] | None:
    """Los avisos del verificador para el partido en ese lugar; None si algo lo bloquea. Se
    revisa el calendario que importa: ese día y los partidos de sus equipos."""
    dia = timezone.localtime(inicio).date()
    calendario: dict[Any, tuple[str, datetime]] = {
        p.pk: (p.cancha.codigo, hora_local(p.inicio))
        for p in partidos
        if p.cancha is not None
        and p.inicio is not None
        and (
            timezone.localtime(p.inicio).date() == dia
            or p.local_id in equipos
            or p.visitante_id in equipos
        )
    }
    calendario[partido.pk] = (cancha.codigo, hora_local(inicio))
    choques = [c for c in choques_del_calendario(problema, calendario) if partido.pk in c.partidos]
    if any(c.bloquea for c in choques):
        return None
    return [m for c in choques for m in c.motivos]
