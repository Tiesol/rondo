"""Partidos de hoy (T11.11): por cancha y hora, con su estado y el atraso de los que siguen."""

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

from django.utils import timezone

from dominio.hoy import EnCancha, atrasos, sin_iniciar
from torneo.models import Equipo, Partido, Torneo
from torneo.presentacion import escudo
from torneo.servicios.partido import fin_esperado, minuto_actual, resultado_de


def _lado(equipo: Equipo | None, texto: str) -> dict[str, Any]:
    if equipo is None:
        return {"nombre": texto, "escudo": None}
    return {"nombre": equipo.nombre, "escudo": escudo(equipo)}


def estado(partido: Partido, ahora: datetime) -> tuple[str, str]:
    """El texto corto del estado y su color: ("2T 27'", "aviso")."""
    if partido.no_se_presento:
        return "W.O.", "neutro"
    if partido.estado == Partido.Estado.JUGADO:
        return "Terminado", "bien"
    if partido.estado == Partido.Estado.EN_JUEGO:
        minuto = minuto_actual(partido)
        match partido.tiempo:
            case Partido.Tiempo.DESCANSO:
                return "Descanso", "aviso"
            case Partido.Tiempo.SEGUNDO_TIEMPO:
                return f"2T {minuto}'", "aviso"
            case _:
                return f"1T {minuto}'", "aviso"
    if partido.inicio and sin_iniciar(_en_cancha(partido), ahora):
        return "Sin iniciar", "error"
    return "Por jugar", "neutro"


def _en_cancha(partido: Partido) -> EnCancha:
    assert partido.inicio is not None
    return EnCancha(
        id=partido.pk,
        programado=partido.inicio,
        minutos_partido=partido.categoria.minutos_partido,
        minutos_turno=partido.categoria.minutos_turno,
        inicio_real=partido.inicio_real,
        fin_real=partido.fin_real,
        fin_esperado=fin_esperado(partido) if partido.estado == Partido.Estado.EN_JUEGO else None,
    )


def partidos_de_hoy(torneo: Torneo, dia: date) -> list[dict[str, Any]]:
    ahora = timezone.now()
    desde = timezone.make_aware(datetime.combine(dia, time.min))
    partidos = (
        Partido.objects.filter(
            categoria__torneo=torneo,
            inicio__gte=desde,
            inicio__lt=desde + timedelta(days=1),
            cancha__isnull=False,
        )
        .select_related("categoria__torneo", "cancha__padre", "local__club", "visitante__club")
        .order_by("cancha__codigo", "inicio")
    )
    por_cancha: dict[Any, list[Partido]] = defaultdict(list)
    for partido in partidos:
        por_cancha[partido.cancha].append(partido)
    secciones = []
    for cancha, suyos in por_cancha.items():
        atraso = atrasos([_en_cancha(p) for p in suyos if p.no_se_presento == ""], ahora)
        nombre = cancha.nombre
        if cancha.padre is not None:
            nombre = (
                f"{cancha.padre.nombre} · mitad {cancha.codigo.removeprefix(cancha.padre.codigo)}"
            )
        filas = []
        for p in suyos:
            texto, color = estado(p, ahora)
            filas.append(
                {
                    "pk": p.pk,
                    "hora": timezone.localtime(p.inicio).strftime("%H:%M"),
                    "categoria": str(p.categoria),
                    "nombre": p.nombre,
                    "local": _lado(p.local, p.texto_local),
                    "visitante": _lado(p.visitante, p.texto_visitante),
                    "marcador": resultado_de(p).marcador if p.empezado else None,
                    "estado": texto,
                    "color": color,
                    "atraso": atraso.get(p.pk, 0),
                }
            )
        secciones.append({"nombre": nombre, "codigo": cancha.codigo, "partidos": filas})
    return secciones
