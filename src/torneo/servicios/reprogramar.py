"""Reprogramación (T5.3): propuestas para un bloqueo, y aplicar una con su historial.

Las propuestas se guardan en una Corrida de tipo reprogramar, junto con una firma del
calendario: si el calendario cambia antes de aplicar, la propuesta ya no vale y se rechaza.
"""

import hashlib
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db import transaction
from django.utils import timezone

from dominio.programador.reprogramar import proponer
from torneo.models import Bloqueo, Cambio, Cancha, Corrida, Partido, Torneo
from torneo.servicios.programador import (
    calendario_actual,
    partidos_del_torneo,
    problema_del_torneo,
    verificar_torneo,
)


class NoSePuedeAplicar(Exception):
    """La propuesta ya no vale (el calendario cambió) o dejaría choques."""


def firma(partidos: list[Partido]) -> str:
    """Una huella del calendario: cambia si se mueve cualquier partido."""
    lineas = sorted(
        f"{p.pk}:{p.cancha_id}:{p.inicio.isoformat() if p.inicio else ''}" for p in partidos
    )
    return hashlib.sha256("\n".join(lineas).encode()).hexdigest()


def _usuario(usuario: AbstractBaseUser | AnonymousUser | None) -> Any:
    return usuario if usuario is not None and usuario.is_authenticated else None


def ventana_de(momento: datetime) -> tuple[datetime, datetime]:
    """Ese fin de semana y el siguiente: del lunes de esa semana a dos semanas después."""
    local = timezone.localtime(momento).replace(tzinfo=None)
    lunes = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0)
    return lunes, lunes + timedelta(days=14)


def calcular_propuestas(
    bloqueo: Bloqueo, usuario: AbstractBaseUser | AnonymousUser | None = None
) -> Corrida:
    torneo = bloqueo.torneo
    comienzo = timezone.now()
    partidos = partidos_del_torneo(torneo)
    desde, hasta = ventana_de(bloqueo.inicio)
    propuestas = proponer(
        problema_del_torneo(torneo, partidos),
        calendario_actual(partidos),
        desde=desde,
        hasta=hasta,
        segundos=settings.PROGRAMADOR_SEGUNDOS,
        trabajadores=settings.PROGRAMADOR_TRABAJADORES,
    )
    return Corrida.objects.create(
        torneo=torneo,
        tipo=Corrida.Tipo.REPROGRAMAR,
        estado=Corrida.Estado.TERMINADA,
        usuario=_usuario(usuario),
        parametros={"bloqueo": bloqueo.pk, "motivo": bloqueo.motivo},
        duracion=(timezone.now() - comienzo).total_seconds(),
        resultado={
            "firma": firma(partidos),
            "propuestas": [
                [
                    {
                        "partido": m.partido,
                        "antes": [m.antes[0], m.antes[1].isoformat()] if m.antes else None,
                        "despues": [m.despues[0], m.despues[1].isoformat()],
                    }
                    for m in propuesta.movimientos
                ]
                for propuesta in propuestas
            ],
        },
    )


@transaction.atomic
def aplicar(
    corrida: Corrida, indice: int, usuario: AbstractBaseUser | AnonymousUser | None = None
) -> list[Cambio]:
    torneo = Torneo.objects.select_for_update().get(pk=corrida.torneo_id)
    partidos = partidos_del_torneo(torneo)
    if firma(partidos) != corrida.resultado.get("firma"):
        raise NoSePuedeAplicar(
            "El calendario cambió después de calcular las propuestas. Vuelve a calcularlas."
        )
    antes = verificar_torneo(torneo)
    canchas = {c.codigo: c for c in Cancha.objects.filter(torneo=torneo)}
    por_id = {p.pk: p for p in partidos}
    cambios = []
    for movimiento in corrida.resultado["propuestas"][indice]:
        partido = por_id[movimiento["partido"]]
        codigo, cuando = movimiento["despues"]
        cambios.append(
            Cambio(
                partido=partido,
                cancha_antes=partido.cancha,
                inicio_antes=partido.inicio,
                cancha_despues=canchas[codigo],
                inicio_despues=timezone.make_aware(datetime.fromisoformat(cuando)),
                usuario=_usuario(usuario),
                motivo=corrida.parametros.get("motivo", ""),
                corrida=corrida,
            )
        )
        partido.cancha = canchas[codigo]
        partido.inicio = timezone.make_aware(datetime.fromisoformat(cuando))
        partido.estado = Partido.Estado.PROGRAMADO
        partido.save(update_fields=["cancha", "inicio", "estado"])
    # Ningún tipo de choque puede aumentar (puede haber otros bloqueos todavía sin resolver).
    despues = verificar_torneo(torneo)
    if any(cantidad > antes.get(tipo, 0) for tipo, cantidad in despues.items()):
        raise NoSePuedeAplicar("La propuesta dejaría choques nuevos. No se aplicó.")
    return Cambio.objects.bulk_create(cambios)
