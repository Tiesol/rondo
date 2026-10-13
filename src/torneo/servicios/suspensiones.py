"""Suspensiones de una categoría (T8.9): de las tarjetas, las multas y las que marca la
organización a mano. Las reglas están en dominio.suspensiones; acá se juntan los datos."""

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone

from dominio.config import Reglas
from dominio.suspensiones import Incidente, Suspension, incidentes_de_tarjetas, suspendidos
from torneo.models import (
    CategoriaNivel,
    Evento,
    Jugador,
    MultaPagada,
    Partido,
    SuspensionManual,
    Torneo,
)

_LEJOS = timezone.make_aware(datetime(9999, 1, 1))


def _orden(categoria: CategoriaNivel) -> dict[Any, list[Any]]:
    """Los partidos de cada equipo en el orden en que se juegan (los sin fecha, al final)."""
    partidos = sorted(
        categoria.partidos.all(), key=lambda p: (p.inicio or _LEJOS, p.fecha or 0, p.pk)
    )
    orden: dict[Any, list[Any]] = defaultdict(list)
    for p in partidos:
        for equipo in (p.local_id, p.visitante_id):
            if equipo is not None:
                orden[equipo].append(p.pk)
    return orden


def suspensiones_de(categoria: CategoriaNivel) -> list[Suspension]:
    reglas = Reglas.model_validate(categoria.torneo.reglas)
    orden = _orden(categoria)
    eventos = Evento.objects.filter(
        partido__categoria=categoria, jugador__isnull=False, tipo__in=["amarilla", "roja"]
    ).values_list("jugador_id", "partido_id", "tipo")
    jugadores = Jugador.objects.filter(equipo__categoria=categoria)
    equipo_de = dict(jugadores.values_list("pk", "equipo_id"))
    multas = MultaPagada.objects.filter(partido__categoria=categoria)
    pagadas = set(multas.values_list("jugador_id", "partido_id"))
    incidentes = incidentes_de_tarjetas(
        [e for e in eventos if e[0] in equipo_de],
        equipo_de=equipo_de,
        edad=categoria.edad,
        orden=orden,
        pagadas=pagadas,
        doble_amarilla_desde=reglas.doble_amarilla_desde,
        partidos_por_roja=reglas.partidos_por_roja_directa,
        amarillas_acumuladas=reglas.amarillas_acumuladas,
    )
    incidentes += [
        Incidente(s.jugador_id, s.jugador.equipo_id, s.partido_id, s.partidos, s.motivo)
        for s in SuspensionManual.objects.filter(partido__categoria=categoria).select_related(
            "jugador"
        )
    ]
    return suspendidos(incidentes, orden)


def suspendidos_en(partido: Partido) -> list[tuple[Jugador, str]]:
    """Quién no puede jugar este partido, y por qué."""
    propias = [s for s in suspensiones_de(partido.categoria) if s.partido == partido.pk]
    jugadores = Jugador.objects.select_related("persona").in_bulk([s.jugador for s in propias])
    return [(jugadores[s.jugador], s.motivo) for s in propias if s.jugador in jugadores]


def multas_de(partido: Partido) -> list[tuple[Jugador, bool]]:
    """Las dobles amarillas de este partido que llevan multa, y si se pagó (P74)."""
    reglas = Reglas.model_validate(partido.categoria.torneo.reglas)
    if partido.categoria.edad < reglas.doble_amarilla_desde:
        return []
    cuenta: dict[Any, int] = defaultdict(int)
    for jugador in partido.eventos.filter(tipo="amarilla", jugador__isnull=False).values_list(
        "jugador_id", flat=True
    ):
        cuenta[jugador] += 1
    dobles = [j for j, n in cuenta.items() if n >= 2]
    pagadas = set(partido.multas.values_list("jugador_id", flat=True))
    jugadores = Jugador.objects.select_related("persona").in_bulk(dobles)
    return [(jugadores[j], j in pagadas) for j in dobles if j in jugadores]


def marcar_multa(partido: Partido, jugador: Jugador, *, pagada: bool, usuario: Any) -> None:
    if pagada:
        MultaPagada.objects.get_or_create(
            partido=partido,
            jugador=jugador,
            defaults={"registrada_por": usuario if isinstance(usuario, User) else None},
        )
    else:
        MultaPagada.objects.filter(partido=partido, jugador=jugador).delete()


def suspender_a_mano(
    partido: Partido, jugador: Jugador, *, partidos: int, motivo: str, usuario: Any
) -> SuspensionManual:
    return SuspensionManual.objects.create(
        partido=partido,
        jugador=jugador,
        partidos=max(1, partidos),
        motivo=motivo.strip() or "Suspensión de la organización",
        creada_por=usuario if isinstance(usuario, User) else None,
    )


def jugadores_del_partido(partido: Partido) -> Q:
    return Q(equipo_id__in=[partido.local_id, partido.visitante_id])


def suspendidos_del_dia(torneo: Torneo, dia: date) -> list[dict[str, Any]]:
    """T9.2: quién no puede jugar ese día, con su equipo, el partido y el motivo."""
    desde = timezone.make_aware(datetime.combine(dia, time.min))
    del_dia = {
        p.pk: p
        for p in Partido.objects.filter(
            categoria__torneo=torneo, inicio__gte=desde, inicio__lt=desde + timedelta(days=1)
        ).select_related("categoria__torneo", "local", "visitante", "cancha")
    }
    filas = []
    for categoria in {p.categoria for p in del_dia.values()}:
        propias = [s for s in suspensiones_de(categoria) if s.partido in del_dia]
        jugadores = Jugador.objects.select_related("persona", "equipo").in_bulk(
            [s.jugador for s in propias]
        )
        for s in propias:
            if s.jugador not in jugadores:
                continue
            partido = del_dia[s.partido]
            filas.append(
                {
                    "jugador": jugadores[s.jugador],
                    "partido": partido,
                    "hora": timezone.localtime(partido.inicio).strftime("%H:%M")
                    if partido.inicio
                    else "",
                    "motivo": s.motivo,
                }
            )
    return sorted(filas, key=lambda f: (f["hora"], str(f["jugador"].persona)))
