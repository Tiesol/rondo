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
from dominio.fixture import SeriesInvalidas, armar_fixture
from dominio.formatos import FormatoFaltante, Formatos, cargar_formatos
from torneo.models import CategoriaNivel, Equipo, Partido, Serie, Torneo


class FixtureNoSePuede(Exception):
    """El fixture de la categoría no se puede generar o rehacer; el mensaje dice por qué."""


@cache
def formatos() -> Formatos:
    return cargar_formatos(settings.FORMATOS)


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
    if partidos.filter(estado=Partido.Estado.JUGADO).exists():
        raise FixtureNoSePuede(
            f"{categoria} ya tiene partidos jugados: su fixture no se puede rehacer (FIX-09)."
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
    try:
        formato = formatos().para(len(equipos))
    except FormatoFaltante as error:
        raise FixtureNoSePuede(f"{categoria}: {error}") from None
    reglas = Reglas.model_validate(categoria.torneo.reglas)
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
