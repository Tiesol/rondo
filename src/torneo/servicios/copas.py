"""Copas por club (T13.24, P30): la Copa Rotativa ya no se entrega, pero la organización quiere
saber qué copas ganó cada club. Sale solo de las finales jugadas: el ganador es campeón y el
otro, subcampeón. Sin datos de personas: se puede mostrar en la página pública."""

from dataclasses import dataclass, field

from torneo.models import Partido, Torneo
from torneo.servicios.partido import resultado_de


@dataclass
class CopasDeUnClub:
    club: str
    oro: list[str] = field(default_factory=list)  # categorías donde fue campeón de Oro
    plata: list[str] = field(default_factory=list)
    subcampeon_oro: list[str] = field(default_factory=list)
    subcampeon_plata: list[str] = field(default_factory=list)


def copas_por_club(torneo: Torneo) -> list[CopasDeUnClub]:
    """Por club, ordenado por Copas de Oro, después de Plata y después por nombre."""
    finales = (
        Partido.objects.filter(
            categoria__torneo=torneo,
            fase=Partido.Fase.ELIMINACION,
            ronda="final",
            copa__in=["oro", "plata"],
            estado=Partido.Estado.JUGADO,
        )
        .select_related("categoria__torneo", "local__club", "visitante__club")
        .order_by("categoria__edad", "categoria__nivel")
    )
    clubes: dict[str, CopasDeUnClub] = {}
    for final in finales:
        if final.local is None or final.visitante is None:
            continue
        ganador = resultado_de(final).ganador
        if ganador is None:
            continue
        campeon, sub = (
            (final.local, final.visitante) if ganador == "local" else (final.visitante, final.local)
        )
        categoria = str(final.categoria)
        for equipo, lista in ((campeon, final.copa), (sub, f"subcampeon_{final.copa}")):
            fila = clubes.setdefault(equipo.club.nombre, CopasDeUnClub(equipo.club.nombre))
            getattr(fila, lista).append(categoria)
    return sorted(clubes.values(), key=lambda f: (-len(f.oro), -len(f.plata), f.club))
