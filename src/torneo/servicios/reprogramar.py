"""Reprogramación (T5.3): propuestas para un bloqueo, y aplicar una con su historial.

Las propuestas se guardan en una Corrida de tipo reprogramar, junto con una firma del
calendario: si el calendario cambia antes de aplicar, la propuesta ya no vale y se rechaza.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db import transaction
from django.utils import timezone

from dominio.config import Reglas
from dominio.franjas import proximo
from dominio.programador.relajar import Relajar
from dominio.programador.reprogramar import proponer
from torneo.models import Bloqueo, Cambio, Cancha, Corrida, Equipo, Franja, Partido, Torneo
from torneo.servicios.programador import (
    ahora_local,
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
    bloqueo: Bloqueo,
    usuario: AbstractBaseUser | AnonymousUser | None = None,
    relajar: Relajar | None = None,
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
        relajar=relajar,
    )


def calcular_propuestas_en(
    torneo: Torneo,
    desde: datetime,
    hasta: datetime,
    *,
    motivo: str,
    origen: dict[str, Any],
    usuario: AbstractBaseUser | AnonymousUser | None = None,
    preferidas: list[Franja] | None = None,
    relajar: Relajar | None = None,
) -> Corrida:
    """Propuestas que solo mueven (o ubican) partidos entre desde y hasta (hora local).

    Nunca propone nada antes de ahora (B1). Con `preferidas` (B1), lo que no tiene lugar se
    ubica primero en ese tiempo agregado. Con `relajar` (B6), las reglas se aflojan solo para
    esta corrida, y la corrida guarda qué se aflojó."""
    comienzo = timezone.now()
    ahora = ahora_local()
    desde = max(desde, ahora)
    partidos = partidos_del_torneo(torneo)
    problema = problema_del_torneo(
        torneo, partidos, desde=ahora, relajar=relajar, ventana=(desde, hasta)
    )
    elegidas = [
        e
        for e in problema.extras
        for f in preferidas or []
        if hora_local(f.inicio) <= e.desde and e.hasta <= hora_local(f.fin)
    ]
    propuestas = proponer(
        problema,
        calendario_actual(partidos),
        desde=desde,
        hasta=hasta,
        cuantas=PROPUESTAS,
        # El límite se reparte: son hasta tres resoluciones dentro del mismo request.
        segundos=max(5, settings.PROGRAMADOR_SEGUNDOS // PROPUESTAS),
        trabajadores=settings.PROGRAMADOR_TRABAJADORES,
        preferidas=tuple(elegidas),
    )
    return Corrida.objects.create(
        torneo=torneo,
        tipo=Corrida.Tipo.REPROGRAMAR,
        estado=Corrida.Estado.TERMINADA,
        usuario=_usuario(usuario),
        parametros={
            **origen,
            "motivo": motivo,
            "relajar": relajar.a_dict() if relajar else {},
            "desde": desde.isoformat(),
            "hasta": hasta.isoformat(),
        },
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
    relajar = Relajar.desde_dict(corrida.parametros.get("relajar") or {})
    antes = verificar_torneo(torneo, relajar=relajar)
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
    despues = verificar_torneo(torneo, relajar=relajar)
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


@dataclass
class Donde:
    """Dónde se juega lo suspendido (B1): un día y un horario, en las canchas elegidas."""

    dia: date
    desde: time = time(16, 0)
    hasta: time = time(20, 0)
    canchas: list[Cancha] = field(default_factory=list)  # vacío: todas


def donde_por_defecto(torneo: Torneo, dia_suspendido: date) -> Donde:
    """El próximo jueves (la regla `dia_para_reprogramar`), de 16 a 20."""
    reglas = Reglas.model_validate(torneo.reglas)
    return Donde(proximo(dia_suspendido + timedelta(days=1), reglas.dia_para_reprogramar))


def _del_dia(torneo: Torneo, dia: date) -> tuple[datetime, datetime]:
    desde = timezone.make_aware(datetime.combine(dia, time.min))
    return desde, desde + timedelta(days=1)


@dataclass
class VistaDeSuspension:
    """Lo que pasa si se suspende el día, para decirlo antes (B7)."""

    se_suspenden: list[Partido]
    en_juego: list[Partido]  # B3: no se sacan del calendario
    jugados: int


def vista_de_suspension(torneo: Torneo, dia: date) -> VistaDeSuspension:
    desde, hasta = _del_dia(torneo, dia)
    del_dia = Partido.objects.filter(
        categoria__torneo=torneo, inicio__gte=desde, inicio__lt=hasta
    ).select_related("local", "visitante", "categoria")
    return VistaDeSuspension(
        se_suspenden=[
            p for p in del_dia if p.estado in (Partido.Estado.PROGRAMADO, Partido.Estado.PENDIENTE)
        ],
        en_juego=[p for p in del_dia if p.estado == Partido.Estado.EN_JUEGO],
        jugados=sum(1 for p in del_dia if p.estado == Partido.Estado.JUGADO),
    )


def suspender_dia(
    torneo: Torneo,
    dia: date,
    usuario: AbstractBaseUser | AnonymousUser | None = None,
    *,
    donde: Donde | None = None,
    relajar: Relajar | None = None,
) -> Corrida:
    """Suspende las franjas del día (B1). Sus partidos no jugados quedan sin programar (con su
    Cambio), salvo los que están en juego (B3), que la organización decide. Crea el tiempo
    donde se juega lo suspendido (por defecto, el próximo jueves de 16 a 20) y calcula
    propuestas para ubicarlo ahí primero; lo que no entra va a los días siguientes, moviendo lo
    menos posible. Nunca propone nada antes de ahora."""
    motivo = "Día suspendido"
    donde = donde or donde_por_defecto(torneo, dia)
    with transaction.atomic():
        Torneo.objects.select_for_update().get(pk=torneo.pk)
        desde, hasta = _del_dia(torneo, dia)
        torneo.franjas.filter(inicio__gte=desde, inicio__lt=hasta).update(suspendida=True)
        partidos = list(
            Partido.objects.filter(
                categoria__torneo=torneo, inicio__gte=desde, inicio__lt=hasta
            ).exclude(estado__in=[Partido.Estado.JUGADO, Partido.Estado.EN_JUEGO])
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
        franja = _crear_tiempo(torneo, donde)
    cuando, _ = _del_dia(torneo, donde.dia)
    inicio_ventana, fin_ventana = ventana_de(min(desde, cuando))
    fin_ventana = max(fin_ventana, hora_local(cuando) + timedelta(days=8))
    return calcular_propuestas_en(
        torneo,
        inicio_ventana,
        fin_ventana,
        motivo=motivo,
        origen={"dia": dia.isoformat(), "franja_extra": franja.pk},
        usuario=usuario,
        preferidas=[franja],
        relajar=relajar,
    )


def _crear_tiempo(torneo: Torneo, donde: Donde) -> Franja:
    inicio = timezone.make_aware(datetime.combine(donde.dia, donde.desde))
    fin = timezone.make_aware(datetime.combine(donde.dia, donde.hasta))
    franja = Franja.objects.filter(
        torneo=torneo, inicio=inicio, fin=fin, tipo=Franja.Tipo.ENTRE_SEMANA
    ).first()
    if franja is None:
        franja = Franja.objects.create(
            torneo=torneo, inicio=inicio, fin=fin, tipo=Franja.Tipo.ENTRE_SEMANA
        )
        franja.canchas.set(donde.canchas)
    franja.suspendida = False
    franja.save(update_fields=["suspendida"])
    return franja


@dataclass
class VistaDeReanudar:
    """Lo que pasa si se reanuda el día (B2)."""

    reabre: int  # franjas
    vuelven: list[Partido]  # siguen sin lugar: vuelven adonde estaban
    en_otro_lado: list[Partido]  # ya se ubicaron: quedan donde están
    franja_extra: Franja | None  # el tiempo agregado al suspender, si quedó vacío se quita


def _suspendidos_del_dia(torneo: Torneo, dia: date) -> dict[int, Cambio]:
    """El último Cambio "Día suspendido" de cada partido de ese día."""
    desde, hasta = _del_dia(torneo, dia)
    cambios = (
        Cambio.objects.filter(
            partido__categoria__torneo=torneo,
            motivo="Día suspendido",
            inicio_antes__gte=desde,
            inicio_antes__lt=hasta,
        )
        .select_related("partido__local", "partido__visitante", "partido__categoria")
        .order_by("fecha", "pk")
    )
    return {c.partido_id: c for c in cambios}


def vista_de_reanudar(torneo: Torneo, dia: date) -> VistaDeReanudar:
    desde, hasta = _del_dia(torneo, dia)
    cohorte = _suspendidos_del_dia(torneo, dia)
    vuelven, en_otro_lado = [], []
    for cambio in cohorte.values():
        partido = cambio.partido
        if partido.estado == Partido.Estado.PENDIENTE and partido.inicio is None:
            vuelven.append(partido)
        elif partido.estado == Partido.Estado.PROGRAMADO:
            en_otro_lado.append(partido)
    franja = None
    corrida = (
        Corrida.objects.filter(
            torneo=torneo, tipo=Corrida.Tipo.REPROGRAMAR, parametros__dia=dia.isoformat()
        )
        .exclude(parametros__franja_extra=None)
        .order_by("-pk")
        .first()
    )
    if corrida is not None:
        franja = Franja.objects.filter(pk=corrida.parametros.get("franja_extra")).first()
        if (
            franja is not None
            and Partido.objects.filter(
                categoria__torneo=torneo, inicio__gte=franja.inicio, inicio__lt=franja.fin
            ).exists()
        ):
            franja = None  # tiene partidos: se queda
    return VistaDeReanudar(
        reabre=torneo.franjas.filter(inicio__gte=desde, inicio__lt=hasta, suspendida=True).count(),
        vuelven=vuelven,
        en_otro_lado=en_otro_lado,
        franja_extra=franja,
    )


@transaction.atomic
def reanudar_dia(
    torneo: Torneo, dia: date, usuario: AbstractBaseUser | AnonymousUser | None = None
) -> VistaDeReanudar:
    """B2: vuelve a abrir las franjas del día. Los partidos que siguen sin lugar vuelven adonde
    estaban (el Cambio guarda dónde); los que ya se ubicaron en otro lado quedan donde están."""
    Torneo.objects.select_for_update().get(pk=torneo.pk)
    vista = vista_de_reanudar(torneo, dia)
    desde, hasta = _del_dia(torneo, dia)
    torneo.franjas.filter(inicio__gte=desde, inicio__lt=hasta).update(suspendida=False)
    cohorte = _suspendidos_del_dia(torneo, dia)
    canchas = {c.pk: c for c in Cancha.objects.filter(torneo=torneo)}
    for partido in vista.vuelven:
        antes = cohorte[partido.pk]
        if antes.cancha_antes_id is None or antes.inicio_antes is None:
            continue
        Cambio.objects.create(
            partido=partido,
            cancha_despues=canchas.get(antes.cancha_antes_id),
            inicio_despues=antes.inicio_antes,
            usuario=_usuario(usuario),
            motivo="Día reanudado",
        )
        partido.cancha = canchas.get(antes.cancha_antes_id)
        partido.inicio = antes.inicio_antes
        partido.estado = Partido.Estado.PROGRAMADO
        partido.save(update_fields=["cancha", "inicio", "estado"])
    if vista.franja_extra is not None:
        vista.franja_extra.delete()
    return vista


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
