"""Bloqueos de la ACF (T5.1): qué partidos programados chocan con uno."""

from collections.abc import Iterable
from datetime import datetime, timedelta

from django.db.models import Q

from torneo.models import Bloqueo, Equipo, Partido, Torneo


def partidos_que_chocan(
    torneo: Torneo, equipos: Iterable[Equipo], inicio: datetime, fin: datetime
) -> list[Partido]:
    """Los partidos programados de esos equipos que se juegan, aunque sea en parte, entre
    inicio y fin."""
    ids = [e.pk for e in equipos]
    candidatos = (
        Partido.objects.filter(
            Q(local__in=ids) | Q(visitante__in=ids),
            categoria__torneo=torneo,
            inicio__isnull=False,
            inicio__lt=fin,
            inicio__gte=inicio - timedelta(hours=3),
        )
        .select_related("categoria__torneo", "cancha", "local", "visitante")
        .order_by("inicio")
    )
    return [
        p
        for p in candidatos
        if p.inicio is not None
        and p.inicio + timedelta(minutes=p.categoria.minutos_partido) > inicio
    ]


def chocan_con_bloqueos(torneo: Torneo) -> dict[int, str]:
    """T13.16: los partidos programados que chocan con algún bloqueo, con su motivo. Hay pocos
    bloqueos: una consulta por bloqueo."""
    chocan: dict[int, str] = {}
    for bloqueo in Bloqueo.objects.filter(torneo=torneo).prefetch_related("equipos"):
        for partido in partidos_que_chocan(
            torneo, bloqueo.equipos.all(), bloqueo.inicio, bloqueo.fin
        ):
            chocan.setdefault(partido.pk, bloqueo.motivo)
    return chocan
