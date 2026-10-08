"""Servicio de programación (T4.5): de la base al solver y de vuelta, con su Corrida.

Corre dentro del request, con un límite de tiempo (settings.PROGRAMADOR_SEGUNDOS). Antes de
resolver se crea una Corrida "corriendo" con el torneo bloqueado: así no se lanzan dos a la
vez, sin dejar la base tomada mientras el solver trabaja. El resultado se verifica con el
verificador y se guarda antes de responder.
"""

from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from dominio.config import Reglas
from dominio.formatos import FormatoFaltante
from dominio.programador.modelo import PartidoAProgramar, Problema, programar
from dominio.programador.motivos import motivos_sin_ubicar
from dominio.verificador import Bloqueo as BloqueoDelDominio
from dominio.verificador import Escenario, PartidoAgendado, verificar
from torneo.models import Bloqueo, Cancha, CategoriaNivel, Corrida, Partido, Torneo
from torneo.servicios.fixture import formatos
from torneo.servicios.personas import pares_de_equipos

# Una corrida "corriendo" más vieja que su límite más este margen se da por abandonada.
MARGEN_DE_ABANDONO = timedelta(minutes=2)


class ProgramacionEnCurso(Exception):
    """Ya hay una programación corriendo para este torneo."""


def _local(momento: datetime) -> datetime:
    """El dominio trabaja con la hora de Bolivia, sin zona."""
    return timezone.localtime(momento).replace(tzinfo=None)


def _con_zona(momento: datetime) -> datetime:
    return timezone.make_aware(momento)


def _referidos(categoria: CategoriaNivel, cantidad: int) -> dict[str, frozenset[str]]:
    """Clave de cada llave → claves de los partidos a los que se refiere (del formato)."""
    try:
        formato = formatos().para(cantidad)
    except FormatoFaltante:
        return {}
    return {
        llave.clave: frozenset(
            llave.local.participante.partidos_referidos
            + llave.visitante.participante.partidos_referidos
        )
        for llave in formato.eliminacion
    }


def _texto(partido: Partido) -> str:
    local = partido.local.nombre if partido.local else partido.texto_local
    visitante = partido.visitante.nombre if partido.visitante else partido.texto_visitante
    cruce = partido.nombre or f"{local} vs {visitante}"
    return f"{cruce} · {partido.categoria}"


def _problema(torneo: Torneo, partidos: list[Partido]) -> Problema:
    canchas = list(Cancha.objects.filter(torneo=torneo).prefetch_related("mitades"))
    fisicas = {
        c.codigo: frozenset(m.codigo for m in c.mitades.all()) or frozenset({c.codigo})
        for c in canchas
    }
    franjas = sorted((_local(f.inicio), _local(f.fin)) for f in torneo.franjas.all())
    reglas = Reglas.model_validate(torneo.reglas)
    semanas = sorted({desde.isocalendar()[:2] for desde, _ in franjas})
    desde_semana = semanas[reglas.eliminacion_desde_fin_de_semana - 1 :][:1]
    eliminacion_desde = next(
        (desde for desde, _ in franjas if desde.isocalendar()[:2] in desde_semana), None
    )

    # Una sola consulta por todas las categorías: sus canchas y cuántos equipos tienen.
    categorias = {
        c.pk: c
        for c in CategoriaNivel.objects.filter(torneo=torneo)
        .prefetch_related("canchas")
        .annotate(cantidad=Count("equipos", distinct=True))
    }
    compatibles = {
        pk: frozenset(c.codigo for c in cat.canchas.all()) for pk, cat in categorias.items()
    }
    referidos = {pk: _referidos(cat, cat.cantidad) for pk, cat in categorias.items()}
    a_programar = []
    for partido in partidos:
        categoria = partido.categoria
        fijo = None
        quieto = partido.estado == Partido.Estado.JUGADO or partido.fijado
        if quieto and partido.cancha and partido.inicio:
            fijo = (partido.cancha.codigo, _local(partido.inicio))
        a_programar.append(
            PartidoAProgramar(
                id=partido.pk,
                categoria=str(categoria.pk),
                equipos=(partido.local_id, partido.visitante_id),
                minutos_partido=categoria.minutos_partido,
                minutos_turno=categoria.minutos_turno,
                canchas=compatibles[categoria.pk],
                fijo=fijo,
                fase=partido.fase,
                fecha=partido.fecha,
                clave=partido.clave,
                nombre=partido.nombre,
                despues_de=referidos[categoria.pk].get(partido.clave, frozenset()),
            )
        )
    return Problema(
        partidos=tuple(a_programar),
        fisicas=fisicas,
        franjas=tuple(franjas),
        reglas=reglas,
        pares=tuple(pares_de_equipos(torneo)),
        bloqueos=bloqueos_del_torneo(torneo),
        eliminacion_desde=eliminacion_desde,
    )


def bloqueos_del_torneo(torneo: Torneo) -> tuple[BloqueoDelDominio, ...]:
    """Un bloqueo del dominio por equipo bloqueado (P38: uno puede abarcar varios)."""
    return tuple(
        BloqueoDelDominio(equipo.pk, _local(bloqueo.inicio), _local(bloqueo.fin), bloqueo.motivo)
        for bloqueo in Bloqueo.objects.filter(torneo=torneo).prefetch_related("equipos")
        for equipo in bloqueo.equipos.all()
    )


def _choques(problema: Problema, ubicados: dict[Any, tuple[str, datetime]]) -> dict[str, int]:
    agendados = [
        PartidoAgendado(
            id=p.id,
            categoria=p.categoria,
            equipos=p.equipos,
            cancha=ubicados[p.id][0],
            inicio=ubicados[p.id][1],
            minutos_partido=p.minutos_partido,
            minutos_turno=p.minutos_turno,
        )
        for p in problema.partidos
        if p.id in ubicados
    ]
    escenario = Escenario(
        fisicas=problema.fisicas,
        compatibilidad={p.categoria: p.canchas for p in problema.partidos},
        franjas=problema.franjas,
        pares=problema.pares,
        bloqueos=problema.bloqueos,
        reglas=problema.reglas,
    )
    return dict(Counter(c.tipo for c in verificar(agendados, escenario)))


def _empezar(torneo: Torneo, usuario: AbstractBaseUser | AnonymousUser | None) -> Corrida:
    segundos = settings.PROGRAMADOR_SEGUNDOS
    with transaction.atomic():
        Torneo.objects.select_for_update().get(pk=torneo.pk)
        limite = timezone.now() - timedelta(seconds=segundos) - MARGEN_DE_ABANDONO
        if Corrida.objects.filter(
            torneo=torneo, estado=Corrida.Estado.CORRIENDO, inicio__gte=limite
        ).exists():
            raise ProgramacionEnCurso(
                "Ya hay una programación corriendo para este torneo. Espera a que termine."
            )
        return Corrida.objects.create(
            torneo=torneo,
            parametros={"segundos": segundos, "trabajadores": settings.PROGRAMADOR_TRABAJADORES},
            usuario=usuario if usuario is not None and usuario.is_authenticated else None,  # type: ignore[misc]
        )


def programar_torneo(
    torneo: Torneo, usuario: AbstractBaseUser | AnonymousUser | None = None
) -> Corrida:
    corrida = _empezar(torneo, usuario)
    comienzo = timezone.now()
    try:
        partidos = list(
            Partido.objects.filter(categoria__torneo=torneo).select_related(
                "categoria__torneo", "cancha", "local", "visitante"
            )
        )
        problema = _problema(torneo, partidos)
        resultado = programar(
            problema,
            segundos=settings.PROGRAMADOR_SEGUNDOS,
            trabajadores=settings.PROGRAMADOR_TRABAJADORES,
        )
        motivos = motivos_sin_ubicar(problema, resultado)
        choques = _choques(problema, resultado.ubicados)
        _guardar(torneo, partidos, resultado.ubicados)
    except Exception:
        corrida.estado = Corrida.Estado.FALLIDA
        corrida.duracion = (timezone.now() - comienzo).total_seconds()
        corrida.save()
        raise

    por_id: dict[Any, Partido] = {p.pk: p for p in partidos}
    corrida.estado = Corrida.Estado.TERMINADA
    corrida.duracion = (timezone.now() - comienzo).total_seconds()
    corrida.resultado = {
        "estado_solver": resultado.estado,
        "total": len(partidos),
        "ubicados": len(resultado.ubicados),
        "sin_ubicar": [
            {"id": id_, "partido": _texto(por_id[id_]), "motivo": motivos.get(id_, "")}
            for id_ in resultado.sin_ubicar
        ],
        "choques": choques,
    }
    corrida.save()
    return corrida


@transaction.atomic
def _guardar(
    torneo: Torneo, partidos: list[Partido], ubicados: dict[Any, tuple[str, datetime]]
) -> None:
    canchas = {c.codigo: c for c in Cancha.objects.filter(torneo=torneo)}
    cambiados = []
    for partido in partidos:
        if partido.estado == Partido.Estado.JUGADO or partido.fijado:
            continue
        if partido.pk in ubicados:
            codigo, inicio = ubicados[partido.pk]
            partido.cancha, partido.inicio = canchas[codigo], _con_zona(inicio)
            partido.estado = Partido.Estado.PROGRAMADO
        else:
            partido.cancha, partido.inicio = None, None
            partido.estado = Partido.Estado.PENDIENTE
        cambiados.append(partido)
    Partido.objects.bulk_update(cambiados, ["cancha", "inicio", "estado"])
