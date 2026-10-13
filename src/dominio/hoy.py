"""Partidos de hoy (T11.11): el atraso estimado de los que siguen en una cancha, y los que no
empezaron pasada media hora de su horario. Es solo informativo: no mueve nada."""

from collections.abc import Hashable
from dataclasses import dataclass
from datetime import datetime, timedelta

ATRASO_MINIMO = 5  # menos que esto no vale la pena avisarlo
SIN_INICIAR_DESPUES = timedelta(minutes=30)


@dataclass(frozen=True)
class EnCancha:
    id: Hashable
    programado: datetime
    minutos_partido: int
    minutos_turno: int  # el partido más el cambio
    inicio_real: datetime | None = None
    fin_real: datetime | None = None
    fin_esperado: datetime | None = None  # si ya empezó el 2.º tiempo, lo calcula quien llama

    @property
    def cambio(self) -> timedelta:
        return timedelta(minutes=self.minutos_turno - self.minutos_partido)


def atrasos(partidos: list[EnCancha], ahora: datetime) -> dict[Hashable, int]:
    """Los minutos de atraso estimados de cada partido que todavía no empezó, en una cancha."""
    libre: datetime | None = None  # desde cuándo la cancha queda libre
    resultado: dict[Hashable, int] = {}
    for partido in sorted(partidos, key=lambda p: p.programado):
        if partido.fin_real is not None:
            libre = partido.fin_real + partido.cambio
            continue
        if partido.inicio_real is not None:
            fin = partido.fin_esperado or partido.inicio_real + timedelta(
                minutes=partido.minutos_partido
            )
            libre = max(fin, ahora) + partido.cambio
            continue
        empieza = max(partido.programado, ahora, libre or partido.programado)
        minutos = int((empieza - partido.programado).total_seconds() // 60)
        if minutos >= ATRASO_MINIMO:
            resultado[partido.id] = minutos
        libre = empieza + timedelta(minutes=partido.minutos_turno)
    return resultado


def sin_iniciar(partido: EnCancha, ahora: datetime) -> bool:
    """Pasada media hora de su horario y sin empezar: se marca, no se cierra solo (3.4)."""
    return partido.inicio_real is None and ahora > partido.programado + SIN_INICIAR_DESPUES
