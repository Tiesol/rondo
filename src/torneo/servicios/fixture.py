"""Servicio de fixture (T3.4): arma el fixture de una categoría con el dominio y lo guarda.

Las series guardadas se respetan mientras sigan valiendo para los equipos actuales: así la
organización puede editarlas antes de generar (FIX-06). Rehacer un fixture borra el anterior,
solo si la regla lo permite y no hay partidos jugados (FIX-09).
"""

import random
from dataclasses import dataclass, field
from functools import cache

from django.conf import settings
from django.db import transaction

from dominio.config import Reglas
from dominio.fixture import PartidoDelFixture, SeriesInvalidas, armar_fixture
from dominio.formatos import Copa, FormatoFaltante, FormatoParaN, Formatos, cargar_formatos
from dominio.rehacer import planear_rehacer
from torneo.models import CategoriaNivel, Equipo, Partido, Serie, Torneo


class FixtureNoSePuede(Exception):
    """El fixture de la categoría no se puede generar o rehacer; el mensaje dice por qué."""


@cache
def formatos() -> Formatos:
    return cargar_formatos(settings.FORMATOS)


def formato_para(reglas: Reglas, cantidad: int) -> FormatoParaN:
    """El formato de la categoría con las copas que se juegan según las reglas (P62)."""
    sin_copas: frozenset[Copa] = frozenset() if reglas.copa_de_bronce else frozenset({"bronce"})
    return formatos().para(cantidad, sin_copas=sin_copas)


def _series_guardadas(categoria: CategoriaNivel, equipos: list[Equipo]) -> dict[str, list[Equipo]]:
    """Las series guardadas, si tienen exactamente a los equipos de hoy."""
    series = {
        s.nombre: list(s.equipos.order_by("pk"))
        for s in categoria.series.prefetch_related("equipos")
    }
    en_series = sorted(e.pk for lista in series.values() for e in lista)
    if en_series != sorted(e.pk for e in equipos):
        return {}
    return series


def _revisar_que_se_puede(categoria: CategoriaNivel, reglas: Reglas) -> None:
    partidos = categoria.partidos
    if not partidos.exists():
        return
    if not reglas.rehacer_fixture:
        raise FixtureNoSePuede(
            f"{categoria} ya tiene fixture, y la regla del torneo no deja rehacerlo (P44)."
        )
    if partidos.filter(estado__in=[Partido.Estado.EN_JUEGO, Partido.Estado.JUGADO]).exists():
        raise FixtureNoSePuede(
            f"{categoria} ya tiene partidos jugados: usa «Rehacer conservando lo jugado» (T11.15)."
        )


@transaction.atomic
def generar_fixture(
    categoria: CategoriaNivel,
    *,
    nuevo_sorteo: bool = False,
    semilla: int | None = None,
    series: dict[str, list[Equipo]] | None = None,
) -> None:
    """Arma y guarda el fixture. Con nuevo_sorteo, las series se vuelven a sortear; con
    series, se usan esas (las que la organización eligió a mano)."""
    equipos = list(categoria.equipos.select_related("club").order_by("pk"))
    if len(equipos) < 2:
        raise FixtureNoSePuede(f"{categoria} necesita al menos 2 equipos para tener fixture.")
    reglas = Reglas.model_validate(categoria.torneo.reglas)
    try:
        formato = formato_para(reglas, len(equipos))
    except FormatoFaltante as error:
        raise FixtureNoSePuede(f"{categoria}: {error}") from None
    _revisar_que_se_puede(categoria, reglas)

    if series is None and not nuevo_sorteo:
        series = _series_guardadas(categoria, equipos) or None
    try:
        fixture = armar_fixture(
            formato,
            equipos,
            lambda equipo: equipo.club_id,
            semilla=semilla if semilla is not None else random.randrange(1_000_000),
            separar_clubes=reglas.sorteo_separa_clubes,
            mismo_club_fecha_1=reglas.mismo_club_fecha_1,
            series=series,
        )
    except SeriesInvalidas as error:
        raise FixtureNoSePuede(f"{categoria}: {error}") from None

    # T13.21: los fijados conservan su lugar si su cruce sigue en el fixture nuevo.
    fijados = {
        (frozenset((p.local_id, p.visitante_id)), p.fase, p.clave): (p.cancha_id, p.inicio)
        for p in categoria.partidos.filter(fijado=True, inicio__isnull=False)
    }
    categoria.partidos.all().delete()
    categoria.series.all().delete()
    guardadas: dict[str, Serie] = {}
    for nombre, lista in fixture.series.items():
        guardadas[nombre] = Serie.objects.create(categoria=categoria, nombre=nombre)
        guardadas[nombre].equipos.set(lista)
    Partido.objects.bulk_create(
        Partido(
            categoria=categoria,
            fase=p.fase,
            copa=p.copa or "",
            ronda=p.ronda or "",
            clave=p.clave,
            nombre=p.nombre,
            fecha=p.fecha,
            serie=guardadas.get(p.serie or ""),
            local=p.local,
            visitante=p.visitante,
            texto_local=p.texto_local,
            texto_visitante=p.texto_visitante,
        )
        for p in fixture.partidos
    )
    if fijados:
        for nuevo in categoria.partidos.filter(fase=Partido.Fase.GRUPOS):
            clave = (frozenset((nuevo.local_id, nuevo.visitante_id)), nuevo.fase, nuevo.clave)
            if clave in fijados:
                nuevo.cancha_id, nuevo.inicio = fijados.pop(clave)
                nuevo.estado, nuevo.fijado = Partido.Estado.PROGRAMADO, True
                nuevo.save(update_fields=["cancha", "inicio", "estado", "fijado"])


def motivo_desactualizado(
    categoria: CategoriaNivel,
    partidos: list[Partido] | None = None,
    equipos: set[int] | None = None,
) -> str:
    """Por qué el fixture de la categoría ya no corresponde (T7.11), o "" si está al día:
    cambiaron sus equipos o las copas que se juegan (P62). Recibe los partidos y los equipos
    si ya están cargados, para no repetir consultas."""
    if partidos is None:
        partidos = list(categoria.partidos.all())
    if not partidos:
        return ""
    if equipos is None:
        equipos = set(categoria.equipos.values_list("pk", flat=True))
    grupos = [p for p in partidos if p.fase == Partido.Fase.GRUPOS]
    en_el_fixture = {p.local_id for p in grupos} | {p.visitante_id for p in grupos}
    if en_el_fixture - {None} != equipos:
        return "Cambiaron los equipos de la categoría después de armar el fixture."
    reglas = Reglas.model_validate(categoria.torneo.reglas)
    try:
        formato = formato_para(reglas, len(equipos))
    except FormatoFaltante:
        return ""
    if len(grupos) != formato.grupos.cantidad_de_partidos(len(equipos)):
        # Por ejemplo, se borró un equipo con sus partidos (T13.3).
        return "Cambiaron los equipos de la categoría después de armar el fixture."
    if len(partidos) - len(grupos) != len(formato.eliminacion):
        return "Cambiaron las copas que se juegan (Copa de Bronce, P62)."
    return ""


def series_elegidas(
    categoria: CategoriaNivel, asignacion: dict[int, str]
) -> dict[str, list[Equipo]]:
    """Las series a partir de "equipo → letra". Un equipo sin letra es un error claro."""
    series: dict[str, list[Equipo]] = {}
    for equipo in categoria.equipos.order_by("pk"):
        letra = asignacion.get(equipo.pk)
        if not letra:
            raise FixtureNoSePuede(f"Falta elegir la serie de {equipo.nombre}.")
        series.setdefault(letra, []).append(equipo)
    return dict(sorted(series.items()))


@dataclass
class ResultadoDeTodas:
    generadas: list[CategoriaNivel] = field(default_factory=list)
    problemas: list[tuple[CategoriaNivel, str]] = field(default_factory=list)


def generar_fixtures_faltantes(torneo: Torneo) -> ResultadoDeTodas:
    """El fixture de cada categoría con equipos que todavía no lo tiene. No pisa ninguno."""
    resultado = ResultadoDeTodas()
    for categoria in torneo.categorias.filter(
        equipos__isnull=False, partidos__isnull=True
    ).distinct():
        try:
            generar_fixture(categoria)
        except FixtureNoSePuede as error:
            resultado.problemas.append((categoria, str(error)))
        else:
            resultado.generadas.append(categoria)
    return resultado


@dataclass
class VistaPrevia:
    """Lo que hace rehacer conservando lo jugado (T11.15), para mostrarlo antes de confirmar."""

    conservados: list[Partido]
    descartados: list[Partido]
    nuevos: int  # partidos que hay que programar


@transaction.atomic
def rehacer_conservando(categoria: CategoriaNivel, *, aplicar: bool) -> VistaPrevia:
    """T11.15 (P44, P80): con partidos jugados, arma el fixture del formato nuevo eligiendo
    las series que conservan la mayor cantidad de partidos jugados. Los partidos sin jugar que
    siguen existiendo se quedan con su horario; los demás se borran, y los nuevos quedan sin
    programar. Sin `aplicar`, no cambia nada."""
    equipos = list(categoria.equipos.select_related("club").order_by("pk"))
    if len(equipos) < 2:
        raise FixtureNoSePuede(f"{categoria} necesita al menos 2 equipos para tener fixture.")
    reglas = Reglas.model_validate(categoria.torneo.reglas)
    if not reglas.rehacer_fixture:
        raise FixtureNoSePuede("La regla del torneo no deja rehacer el fixture (P44).")
    try:
        formato = formato_para(reglas, len(equipos))
    except FormatoFaltante as error:
        raise FixtureNoSePuede(f"{categoria}: {error}") from None
    viejos = list(categoria.partidos.select_related("local", "visitante"))
    if any(p.empezado for p in viejos if p.fase == Partido.Fase.ELIMINACION):
        raise FixtureNoSePuede("La eliminación ya empezó: el fixture no se rehace.")
    jugados: list[tuple[int, int, int]] = [
        (p.pk, p.local_id, p.visitante_id)
        for p in viejos
        if p.empezado
        and p.fase == Partido.Fase.GRUPOS
        and p.local_id is not None
        and p.visitante_id is not None
    ]
    por_id = {e.pk: e for e in equipos}
    plan = planear_rehacer(formato.grupos, list(por_id), jugados, lambda pk: por_id[pk].club_id)
    series = (
        {nombre: [por_id[pk] for pk in pks] for nombre, pks in plan.series.items()}
        if plan.series
        else None
    )
    fixture = armar_fixture(
        formato,
        equipos,
        lambda equipo: equipo.club_id,
        semilla=random.randrange(1_000_000),
        separar_clubes=reglas.sorteo_separa_clubes,
        mismo_club_fecha_1=reglas.mismo_club_fecha_1,
        series=series,
    )

    # Primero los jugados que se conservan, después los sin jugar con el mismo cruce.
    def par(partido: Partido) -> frozenset[int | None]:
        return frozenset((partido.local_id, partido.visitante_id))

    candidatos = [p for p in viejos if p.pk in plan.conservados] + [
        p for p in viejos if not p.empezado and p.fase == Partido.Fase.GRUPOS
    ]
    llaves = {p.clave: p for p in viejos if p.fase == Partido.Fase.ELIMINACION}
    usados: set[int] = set()
    destino: list[tuple[PartidoDelFixture[Equipo], Partido | None]] = []
    for nuevo in fixture.partidos:
        elegido = None
        if nuevo.fase == "grupos":
            cruce = frozenset(
                (
                    nuevo.local.pk if nuevo.local else None,
                    nuevo.visitante.pk if nuevo.visitante else None,
                )
            )
            elegido = next((p for p in candidatos if p.pk not in usados and par(p) == cruce), None)
        else:
            elegido = llaves.get(nuevo.clave)
        if elegido is not None:
            usados.add(elegido.pk)
        destino.append((nuevo, elegido))
    nuevos = sum(1 for _, elegido in destino if elegido is None or elegido.inicio is None)
    vista = VistaPrevia(
        conservados=[p for p in viejos if p.pk in plan.conservados],
        descartados=[p for p in viejos if p.pk in plan.descartados],
        nuevos=nuevos,
    )
    if not aplicar:
        return vista

    Partido.objects.filter(pk__in=[p.pk for p in viejos if p.pk not in usados]).delete()
    categoria.series.all().delete()
    guardadas: dict[str, Serie] = {}
    for nombre, lista in fixture.series.items():
        guardadas[nombre] = Serie.objects.create(categoria=categoria, nombre=nombre)
        guardadas[nombre].equipos.set(lista)
    for nuevo, elegido in destino:
        serie = guardadas.get(nuevo.serie or "")
        if elegido is not None:
            elegido.fecha, elegido.serie = nuevo.fecha, serie
            elegido.save(update_fields=["fecha", "serie"])
            continue
        Partido.objects.create(
            categoria=categoria,
            fase=nuevo.fase,
            copa=nuevo.copa or "",
            ronda=nuevo.ronda or "",
            clave=nuevo.clave,
            nombre=nuevo.nombre,
            fecha=nuevo.fecha,
            serie=serie,
            local=nuevo.local,
            visitante=nuevo.visitante,
            texto_local=nuevo.texto_local,
            texto_visitante=nuevo.texto_visitante,
        )
    return vista
