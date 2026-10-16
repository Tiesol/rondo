"""Servicio de programación (T4.5): de la base al solver y de vuelta, con su Corrida.

Corre dentro del request, con un límite de tiempo (settings.PROGRAMADOR_SEGUNDOS). Antes de
resolver se crea una Corrida "corriendo" con el torneo bloqueado: así no se lanzan dos a la
vez, sin dejar la base tomada mientras el solver trabaja. El resultado se verifica con el
verificador y se guarda antes de responder.
"""

from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from dominio.config import Reglas
from dominio.formatos import FormatoFaltante, equipos_virtuales, toman_posiciones
from dominio.franjas import DIAS_DE_LA_SEMANA
from dominio.programador.modelo import PartidoAProgramar, Problema, programar
from dominio.programador.motivos import motivos_sin_ubicar
from dominio.programador.relajar import Relajar
from dominio.programador.relajar import aplicar as aplicar_relajar
from dominio.verificador import Bloqueo as BloqueoDelDominio
from dominio.verificador import Choque, Escenario, FranjaExtra, PartidoAgendado, verificar
from torneo.models import Bloqueo, Cancha, CategoriaNivel, Corrida, Equipo, Franja, Partido, Torneo
from torneo.servicios.fixture import formatos
from torneo.servicios.personas import pares_de_equipos

# Una corrida "corriendo" más vieja que su límite más este margen se da por abandonada.
MARGEN_DE_ABANDONO = timedelta(minutes=2)
# La CPU que da el contenedor (cgroups v2): "cuota período", o "max período" sin límite.
CGROUPS = Path("/sys/fs/cgroup")
# Los estados del solver con un calendario (los demás: no encontró ninguno en el tiempo).
CON_SOLUCION = {"OPTIMAL", "FEASIBLE"}


def _cpus(cpu_max: Path) -> float | None:
    try:
        cuota, periodo = cpu_max.read_text().split()[:2]
        return int(cuota) / int(periodo)
    except OSError, ValueError:  # sin el archivo, o "max": sin límite
        return None


def _cpu_max_del_proceso() -> list[Path]:
    """El cpu.max del cgroup del proceso y de los de arriba. En un contenedor, el propio es la
    raíz; fuera de uno (o con systemd), está en /proc/self/cgroup ("0::/ruta")."""
    try:
        ruta = Path("/proc/self/cgroup").read_text().strip().split("::", 1)[1]
    except OSError, IndexError:
        ruta = "/"
    carpeta = CGROUPS / ruta.lstrip("/")
    return [c / "cpu.max" for c in (carpeta, *carpeta.parents) if c.is_relative_to(CGROUPS)]


def poca_cpu(cpu_max: Path | None = None) -> bool:
    """Menos de una CPU (la demo en Render tiene 0,1). Si no se puede saber, no."""
    archivos = [cpu_max] if cpu_max else _cpu_max_del_proceso()
    limites = [c for c in map(_cpus, archivos) if c is not None]
    return bool(limites) and min(limites) < 1


def trabajadores_para_la_cpu(pedidos: int, cpu_max: Path | None = None) -> int:
    """T13.35: con poca CPU, muchos trabajadores se reparten tan poco tiempo que el solver no
    llega a ninguna solución (PROGRESO, H9): se usan 2."""
    return min(pedidos, 2) if poca_cpu(cpu_max) else pedidos


class ProgramacionEnCurso(Exception):
    """Ya hay una programación corriendo para este torneo."""


def hora_local(momento: datetime) -> datetime:
    """El dominio trabaja con la hora de Bolivia, sin zona."""
    return timezone.localtime(momento).replace(tzinfo=None)


def _con_zona(momento: datetime) -> datetime:
    return timezone.make_aware(momento)


@dataclass(frozen=True)
class _DeLaLlave:
    """Lo que el formato dice de cada llave para programarla."""

    despues_de: frozenset[str]  # las claves de los partidos a los que se refiere
    virtuales: frozenset[str]  # sus equipos virtuales (T7.1)
    toma_posiciones: bool


def _llaves(categoria: CategoriaNivel, cantidad: int) -> dict[str, _DeLaLlave]:
    try:
        formato = formatos().para(cantidad)
    except FormatoFaltante:
        return {}
    virtuales = equipos_virtuales(formato)
    posiciones = toman_posiciones(formato)
    # El nombre de la categoría distingue al "ganador de la semi 1" de cada una.
    return {
        llave.clave: _DeLaLlave(
            frozenset(
                llave.local.participante.partidos_referidos
                + llave.visitante.participante.partidos_referidos
            ),
            frozenset(f"{categoria}: {v}" for v in virtuales[llave.clave]),
            llave.clave in posiciones,
        )
        for llave in formato.eliminacion
    }


def _texto(partido: Partido) -> str:
    local = partido.local.nombre if partido.local else partido.texto_local
    visitante = partido.visitante.nombre if partido.visitante else partido.texto_visitante
    cruce = partido.nombre or f"{local} vs {visitante}"
    return f"{cruce} · {partido.categoria}"


def ahora_local() -> datetime:
    return hora_local(timezone.now())


def _recortar(
    franjas: list[tuple[datetime, datetime]], desde: datetime | None
) -> list[tuple[datetime, datetime]]:
    """Nada se ubica antes de `desde` (B4): lo que ya pasó se saca y la franja de ahora empieza
    ahora."""
    if desde is None:
        return franjas
    return [(max(a, desde), b) for a, b in franjas if b > desde and max(a, desde) < b]


def problema_del_torneo(
    torneo: Torneo,
    partidos: list[Partido],
    *,
    desde: datetime | None = None,
    solo_lo_que_falta: bool = False,
    relajar: Relajar | None = None,
    ventana: tuple[datetime, datetime] | None = None,
) -> Problema:
    """El problema del torneo para el solver.

    - `desde` (B4): nunca se ubica nada antes, y los partidos cuya hora ya pasó no se mueven,
      aunque nadie haya cargado su resultado.
    - `solo_lo_que_falta` (B4): todo lo que ya tiene lugar queda fijo; solo se ubica el resto.
    - `relajar` (B6): reglas aflojadas solo para esta corrida, dentro de la `ventana`.
    """
    canchas = list(Cancha.objects.filter(torneo=torneo).prefetch_related("mitades"))
    fisicas = {
        c.codigo: frozenset(m.codigo for m in c.mitades.all()) or frozenset({c.codigo})
        for c in canchas
    }
    vigentes = list(torneo.franjas.filter(suspendida=False).prefetch_related("canchas"))
    todas = sorted(
        (hora_local(f.inicio), hora_local(f.fin)) for f in vigentes if f.tipo == Franja.Tipo.REGULAR
    )
    franjas = _recortar(todas, desde)
    # A4 (P78): lo agregado a mano es tiempo extra: vale en sus canchas y se usa solo si hace falta.
    extras = tuple(
        FranjaExtra(a, b, frozenset(c.codigo for c in f.canchas.all()))
        for f in sorted(vigentes, key=lambda f: f.inicio)
        if f.tipo == Franja.Tipo.ENTRE_SEMANA
        for a, b in _recortar([(hora_local(f.inicio), hora_local(f.fin))], desde)
    )
    reglas = Reglas.model_validate(torneo.reglas)
    semanas = sorted({a.isocalendar()[:2] for a, _ in todas})
    desde_semana = semanas[reglas.eliminacion_desde_fin_de_semana - 1 :][:1]
    eliminacion_desde = next((a for a, _ in todas if a.isocalendar()[:2] in desde_semana), None)

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
    llaves = {pk: _llaves(cat, cat.cantidad) for pk, cat in categorias.items()}
    a_programar = []
    for partido in partidos:
        categoria = partido.categoria
        fijo = pista = None
        if partido.cancha and partido.inicio:
            pista = (partido.cancha.codigo, hora_local(partido.inicio))  # T13.35
            ya_paso = desde is not None and hora_local(partido.inicio) <= desde
            if partido.empezado or ya_paso or solo_lo_que_falta or partido.fijado:
                fijo = pista
        de_la_llave = llaves[categoria.pk].get(partido.clave) if partido.clave else None
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
                despues_de=de_la_llave.despues_de if de_la_llave else frozenset(),
                virtuales=de_la_llave.virtuales if de_la_llave else frozenset(),
                toma_posiciones=de_la_llave.toma_posiciones if de_la_llave else False,
                dias_sin_jugar=frozenset(
                    DIAS_DE_LA_SEMANA.index(d) for d in categoria.dias_sin_jugar
                ),
                temprano=categoria.prefiere_temprano,
                ronda=partido.ronda,
                pista=pista,
            )
        )
    if extras:
        a_programar = _sin_extra_si_entra(torneo, a_programar)
    problema = Problema(
        partidos=tuple(a_programar),
        fisicas=fisicas,
        franjas=tuple(franjas),
        reglas=reglas,
        pares=tuple(pares_de_equipos(torneo)),
        bloqueos=bloqueos_del_torneo(torneo),
        eliminacion_desde=eliminacion_desde,
        extras=extras,
        clubes=dict(
            Equipo.objects.filter(categoria__torneo=torneo).values_list("pk", "club_id")
        ),  # P20
    )
    if relajar is None or relajar.vacio:
        return problema
    chicas = {str(pk) for pk, c in categorias.items() if c.modalidad in ("F8", "F11")}
    return aplicar_relajar(problema, relajar, ventana=ventana, sin_mitades=chicas)


def _sin_extra_si_entra(
    torneo: Torneo, partidos: list[PartidoAProgramar]
) -> list[PartidoAProgramar]:
    """A4 (P78): si un grupo de canchas entra en el horario normal ("¿Entra todo?"), sus
    categorías no usan el tiempo agregado: es solo para lo que no entra. Si todo entra, no se
    restringe nada (el tiempo agregado igual cuesta más que todo lo blando)."""
    from torneo.servicios.capacidad import capacidad_del_torneo

    grupos = capacidad_del_torneo(torneo).total
    if all(g.entra for g in grupos):
        return partidos
    no_entran = {c for g in grupos if not g.entra for c in g.canchas}
    padres = {
        c.codigo: (c.padre.codigo if c.padre else c.codigo)
        for c in Cancha.objects.filter(torneo=torneo).select_related("padre")
    }
    return [
        p
        if p.fijo or {padres.get(c, c) for c in p.canchas} & no_entran
        else replace(p, sin_extra=True)
        for p in partidos
    ]


def bloqueos_del_torneo(torneo: Torneo) -> tuple[BloqueoDelDominio, ...]:
    """Un bloqueo del dominio por equipo bloqueado (P38: uno puede abarcar varios)."""
    return tuple(
        BloqueoDelDominio(
            equipo.pk, hora_local(bloqueo.inicio), hora_local(bloqueo.fin), bloqueo.motivo
        )
        for bloqueo in Bloqueo.objects.filter(torneo=torneo).prefetch_related("equipos")
        for equipo in bloqueo.equipos.all()
    )


def partidos_del_torneo(torneo: Torneo) -> list[Partido]:
    return list(
        Partido.objects.filter(categoria__torneo=torneo).select_related(
            "categoria__torneo", "cancha", "local", "visitante"
        )
    )


def calendario_actual(partidos: list[Partido]) -> dict[Any, tuple[str, datetime]]:
    """Dónde está cada partido programado, en hora local sin zona (como el dominio)."""
    return {
        p.pk: (p.cancha.codigo, hora_local(p.inicio))
        for p in partidos
        if p.cancha is not None and p.inicio is not None
    }


def verificar_torneo(torneo: Torneo, relajar: Relajar | None = None) -> dict[str, int]:
    """Los choques del calendario actual, por tipo (vacío si no hay). Con `relajar` (B6), con
    las mismas reglas aflojadas que usó la corrida."""
    partidos = partidos_del_torneo(torneo)
    problema = problema_del_torneo(torneo, partidos, relajar=relajar)
    return _choques(problema, calendario_actual(partidos))


def _choques(problema: Problema, ubicados: dict[Any, tuple[str, datetime]]) -> dict[str, int]:
    return dict(Counter(c.tipo for c in choques_del_calendario(problema, ubicados)))


def choques_del_calendario(
    problema: Problema, ubicados: dict[Any, tuple[str, datetime]]
) -> list[Choque]:
    """Los choques duros de un calendario (el actual o uno simulado), con sus motivos."""
    agendados = [
        PartidoAgendado(
            id=p.id,
            categoria=p.categoria,
            equipos=p.equipos,
            cancha=ubicados[p.id][0],
            inicio=ubicados[p.id][1],
            minutos_partido=p.minutos_partido,
            minutos_turno=p.minutos_turno,
            fase=p.fase,
            virtuales=p.virtuales,
            toma_posiciones=p.toma_posiciones,
            dias_sin_jugar=p.dias_sin_jugar,
            ronda=p.ronda,
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
        extras=problema.extras,
    )
    return verificar(agendados, escenario)


def _empezar(
    torneo: Torneo, usuario: AbstractBaseUser | AnonymousUser | None, modo: str = "todo"
) -> Corrida:
    segundos = settings.PROGRAMADOR_SEGUNDOS
    escasa = poca_cpu()
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
            parametros={
                "segundos": segundos,
                "trabajadores": min(settings.PROGRAMADOR_TRABAJADORES, 2)
                if escasa
                else settings.PROGRAMADOR_TRABAJADORES,
                "poca_cpu": escasa,
                "modo": modo,
            },
            usuario=usuario if usuario is not None and usuario.is_authenticated else None,  # type: ignore[misc]
        )


@dataclass
class Resumen:
    """Qué hay antes de volver a programar (B4): lo que no se mueve y lo que sí."""

    jugados: int = 0
    sin_resultado: list[Partido] = field(default_factory=list)  # su hora ya pasó
    futuros: int = 0  # programados que "Volver a programar" mueve
    sin_lugar: int = 0

    @property
    def hay_publicados(self) -> bool:
        return bool(self.jugados or self.sin_resultado or self.futuros)


def resumen_antes_de_programar(torneo: Torneo) -> Resumen:
    ahora = timezone.now()
    resumen = Resumen()
    for partido in partidos_del_torneo(torneo):
        if partido.empezado:
            resumen.jugados += 1
        elif partido.inicio is None:
            resumen.sin_lugar += 1
        elif partido.inicio <= ahora:
            resumen.sin_resultado.append(partido)
        else:
            resumen.futuros += 1
    return resumen


def programar_torneo(
    torneo: Torneo,
    usuario: AbstractBaseUser | AnonymousUser | None = None,
    *,
    solo_lo_que_falta: bool = False,
) -> Corrida:
    """Programa el torneo. Nunca ubica antes de ahora y no mueve lo que ya empezó ni lo que su
    hora ya pasó (B4). Con `solo_lo_que_falta`, todo lo que ya tiene lugar queda fijo."""
    corrida = _empezar(torneo, usuario, "faltan" if solo_lo_que_falta else "todo")
    comienzo = timezone.now()
    try:
        partidos = partidos_del_torneo(torneo)
        problema = problema_del_torneo(
            torneo, partidos, desde=ahora_local(), solo_lo_que_falta=solo_lo_que_falta
        )
        resultado = programar(
            problema,
            segundos=settings.PROGRAMADOR_SEGUNDOS,
            trabajadores=corrida.parametros["trabajadores"],
            una_pasada=corrida.parametros["poca_cpu"],
        )
        sin_solucion = resultado.estado not in CON_SOLUCION
        if sin_solucion:
            # T13.35: sin ningún calendario en el tiempo, el que había queda como estaba.
            # Antes se guardaba "nada ubicado" y se borraba todo.
            motivos, choques = {}, {}
        else:
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
        "sin_solucion": sin_solucion,
        "total": len(partidos),
        "ubicados": len(resultado.ubicados),
        "sin_ubicar": []
        if sin_solucion
        else [
            {"id": id_, "partido": _texto(por_id[id_]), "motivo": motivos.get(id_, "")}
            for id_ in resultado.sin_ubicar
        ],
        "choques": choques,
        # B4: los que ya pasaron de hora y nadie cargó: no se mueven, y les falta el resultado.
        "sin_resultado": [
            _texto(p)
            for p in partidos
            if not p.empezado and p.inicio is not None and p.inicio <= comienzo
        ],
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
        if partido.empezado:
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
