"""Reprogramación (T5.3): propuestas para un bloqueo, y aplicar una con su historial.

Las propuestas se guardan en una Corrida de tipo reprogramar, junto con una firma del
calendario: si el calendario cambia antes de aplicar, la propuesta ya no vale y se rechaza.
"""

import hashlib
from datetime import date, datetime, time, timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db import transaction
from django.utils import timezone

from dominio.programador.reprogramar import proponer
from torneo.models import Bloqueo, Cambio, Cancha, Corrida, Equipo, Partido, Torneo
from torneo.servicios.programador import (
    calendario_actual,
    choques_del_calendario,
    hora_local,
    partidos_del_torneo,
    problema_del_torneo,
    verificar_torneo,
)

PROPUESTAS = 3  # PRO-13: 2 o 3 propuestas


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
    """Propuestas para un bloqueo: ese fin de semana y el siguiente."""
    desde, hasta = ventana_de(bloqueo.inicio)
    return calcular_propuestas_en(
        bloqueo.torneo,
        desde,
        hasta,
        motivo=bloqueo.motivo,
        origen={"bloqueo": bloqueo.pk},
        usuario=usuario,
    )


def calcular_propuestas_en(
    torneo: Torneo,
    desde: datetime,
    hasta: datetime,
    *,
    motivo: str,
    origen: dict[str, Any],
    usuario: AbstractBaseUser | AnonymousUser | None = None,
) -> Corrida:
    """Propuestas que solo mueven (o ubican) partidos entre desde y hasta (hora local)."""
    comienzo = timezone.now()
    partidos = partidos_del_torneo(torneo)
    propuestas = proponer(
        problema_del_torneo(torneo, partidos),
        calendario_actual(partidos),
        desde=desde,
        hasta=hasta,
        cuantas=PROPUESTAS,
        # El límite se reparte: son hasta tres resoluciones dentro del mismo request.
        segundos=max(5, settings.PROGRAMADOR_SEGUNDOS // PROPUESTAS),
        trabajadores=settings.PROGRAMADOR_TRABAJADORES,
    )
    return Corrida.objects.create(
        torneo=torneo,
        tipo=Corrida.Tipo.REPROGRAMAR,
        estado=Corrida.Estado.TERMINADA,
        usuario=_usuario(usuario),
        parametros={**origen, "motivo": motivo},
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


class ChoqueAlMover(Exception):
    """El cambio a mano no se guardó. Si `bloquea`, es imposible (T11.2: la cancha o un equipo
    ocupados a la vez, o el partido ya empezó); si no, son avisos que se pueden confirmar."""

    def __init__(self, motivos: list[str], *, bloquea: bool) -> None:
        super().__init__("; ".join(motivos))
        self.motivos = motivos
        self.bloquea = bloquea


@transaction.atomic
def mover_a_mano(
    partido: Partido,
    cancha: Cancha,
    inicio: datetime,
    usuario: AbstractBaseUser | AnonymousUser | None = None,
    *,
    confirmar: bool = False,
) -> Cambio:
    """T5.4 y T11.2: cualquier día, hora y cancha o mitad. El verificador revisa el cambio:
    lo imposible no se guarda; los avisos se guardan si la organización los confirma. Mover
    no fija el partido (1.4): volver a programar todo lo puede mover."""
    if partido.empezado:
        raise ChoqueAlMover(["El partido ya empezó: no se mueve."], bloquea=True)
    torneo = Torneo.objects.select_for_update().get(pk=partido.categoria.torneo_id)
    partidos = partidos_del_torneo(torneo)
    calendario = calendario_actual(partidos)
    calendario[partido.pk] = (cancha.codigo, hora_local(inicio))
    choques = [
        c
        for c in choques_del_calendario(problema_del_torneo(torneo, partidos), calendario)
        if partido.pk in c.partidos
    ]
    bloquean = [m for c in choques if c.bloquea for m in c.motivos]
    if bloquean:
        raise ChoqueAlMover(bloquean, bloquea=True)
    if choques and not confirmar:
        raise ChoqueAlMover([m for c in choques for m in c.motivos], bloquea=False)
    cambio = Cambio.objects.create(
        partido=partido,
        cancha_antes=partido.cancha,
        inicio_antes=partido.inicio,
        cancha_despues=cancha,
        inicio_despues=inicio,
        usuario=_usuario(usuario),
        motivo="Cambio a mano",
    )
    partido.cancha, partido.inicio = cancha, inicio
    partido.estado = Partido.Estado.PROGRAMADO
    partido.save(update_fields=["cancha", "inicio", "estado"])
    return cambio


def suspender_dia(
    torneo: Torneo, dia: date, usuario: AbstractBaseUser | AnonymousUser | None = None
) -> Corrida:
    """Suspende las franjas del día: sus partidos no jugados quedan sin programar (con su
    Cambio), y se calculan propuestas para ubicarlos ese fin de semana o el siguiente."""
    motivo = "Día suspendido"
    with transaction.atomic():
        Torneo.objects.select_for_update().get(pk=torneo.pk)
        desde = timezone.make_aware(datetime.combine(dia, time.min))
        hasta = desde + timedelta(days=1)
        torneo.franjas.filter(inicio__gte=desde, inicio__lt=hasta).update(suspendida=True)
        partidos = list(
            Partido.objects.filter(
                categoria__torneo=torneo, inicio__gte=desde, inicio__lt=hasta
            ).exclude(estado=Partido.Estado.JUGADO)
        )
        Cambio.objects.bulk_create(
            Cambio(
                partido=p,
                cancha_antes_id=p.cancha_id,
                inicio_antes=p.inicio,
                usuario=_usuario(usuario),
                motivo=motivo,
            )
            for p in partidos
        )
        for partido in partidos:
            partido.cancha, partido.inicio = None, None
            partido.estado = Partido.Estado.PENDIENTE
        Partido.objects.bulk_update(partidos, ["cancha", "inicio", "estado"])
    inicio_ventana, fin_ventana = ventana_de(desde)
    return calcular_propuestas_en(
        torneo,
        inicio_ventana,
        fin_ventana,
        motivo=motivo,
        origen={"dia": dia.isoformat()},
        usuario=usuario,
    )


def veces_que_reprogramo(equipo: Equipo) -> int:
    """T10.10: cuántos pedidos de ese equipo ya terminaron en un cambio aplicado."""
    bloqueos = set(equipo.bloqueos.values_list("pk", flat=True))
    corridas = Corrida.objects.filter(
        tipo=Corrida.Tipo.REPROGRAMAR, cambios__isnull=False
    ).distinct()
    return sum(1 for c in corridas if c.parametros.get("bloqueo") in bloqueos)


def afectados_por(bloqueo: Bloqueo) -> list[tuple[Partido, Equipo]]:
    """Los partidos de los equipos del pedido que caen en su horario, con el equipo."""
    equipos = list(bloqueo.equipos.all())
    resultado = []
    for partido in Partido.objects.filter(
        categoria__torneo=bloqueo.torneo, inicio__lt=bloqueo.fin
    ).select_related("local", "visitante", "categoria"):
        if partido.inicio is None or partido.empezado:
            continue
        fin = partido.inicio + timedelta(minutes=partido.categoria.minutos_partido)
        if fin <= bloqueo.inicio:
            continue
        for equipo in equipos:
            if equipo.pk in (partido.local_id, partido.visitante_id):
                resultado.append((partido, equipo))
    return resultado
