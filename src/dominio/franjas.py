"""Franjas con fecha concreta (4.3), en UTC. Se muestran en la zona horaria del torneo."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from dominio.config import ConfigTorneo, DiaSemana

_DIAS: tuple[DiaSemana, ...] = (
    "lunes",
    "martes",
    "miercoles",
    "jueves",
    "viernes",
    "sabado",
    "domingo",
)


@dataclass(frozen=True, slots=True)
class Franja:
    inicio: datetime  # en UTC
    fin: datetime

    @property
    def duracion_min(self) -> int:
        return int((self.fin - self.inicio).total_seconds() // 60)


def franjas_del_torneo(config: ConfigTorneo) -> tuple[Franja, ...]:
    """Una franja por cada día del torneo que tenga horario configurado, en orden."""
    zona = ZoneInfo(config.torneo.zona_horaria)
    franjas: list[Franja] = []
    dia = config.torneo.inicio
    while dia <= config.torneo.fin:
        horario = config.franjas.get(_DIAS[dia.weekday()])
        if horario is not None:
            inicio, fin = (datetime.combine(dia, hora, tzinfo=zona) for hora in horario)
            franjas.append(Franja(inicio.astimezone(UTC), fin.astimezone(UTC)))
        dia += timedelta(days=1)
    return tuple(franjas)
