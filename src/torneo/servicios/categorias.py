"""Agregar una categoría o un nivel a un torneo ya creado (T11.1).

Lo que no se escribe se completa solo: primero desde la otra categoría-nivel del mismo nombre,
después desde la plantilla del torneo (por ejemplo, Sub 15 Femenino, que el asistente deja sin
tildar). Las canchas, las de la plantilla o las de otra categoría con la misma modalidad.
"""

import re

from django.conf import settings
from django.db import transaction

from dominio.canchas import canchas_compatibles
from dominio.config import ConfigTorneo, cargar_config
from dominio.config import Nivel as NivelDeLaPlantilla
from torneo.models import Cancha, CategoriaNivel, Torneo


class NoSePuede(ValueError):
    """La categoría no se puede agregar; el mensaje dice por qué."""


def _plantilla() -> ConfigTorneo:
    return cargar_config(settings.PLANTILLA_TORNEO)


def nombres_de_la_plantilla() -> list[str]:
    return [c.nombre for c in _plantilla().categorias]


@transaction.atomic
def agregar_categoria(
    torneo: Torneo,
    nombre: str,
    nivel: str,
    *,
    modalidad: str = "",
    min_por_tiempo: int | None = None,
    minimo: int | None = None,
    maximo: int | None = None,
) -> CategoriaNivel:
    nombre = " ".join(nombre.split())
    if nivel not in CategoriaNivel.Nivel.values:
        raise NoSePuede("Elige el nivel.")
    hermanas = list(torneo.categorias.filter(categoria__iexact=nombre))
    if any(h.nivel == nivel for h in hermanas):
        raise NoSePuede(f"Ya existe {hermanas[0].categoria} con ese nivel.")
    unico = CategoriaNivel.Nivel.UNICO
    if hermanas and (nivel == unico or any(h.nivel == unico for h in hermanas)):
        raise NoSePuede(f"{hermanas[0].categoria} tiene nivel único: no se le agrega otro nivel.")

    plantilla = _plantilla()
    de_la_plantilla = next(
        (c for c in plantilla.categorias if c.nombre.casefold() == nombre.casefold()), None
    )
    nivel_de_la_plantilla: NivelDeLaPlantilla | None = (
        de_la_plantilla.niveles.get(nivel) if de_la_plantilla else None  # type: ignore[call-overload]
    )
    hermana = hermanas[0] if hermanas else None

    if hermana is not None:
        nombre = hermana.categoria
        edad, anios, genero = hermana.edad, hermana.anios_nacimiento, hermana.genero
        dias, temprano = hermana.dias_sin_jugar, hermana.prefiere_temprano
    elif de_la_plantilla is not None:
        nombre = de_la_plantilla.nombre
        edad, anios = de_la_plantilla.edad, de_la_plantilla.anios_nacimiento
        genero = de_la_plantilla.genero
        dias, temprano = list(de_la_plantilla.dias_sin_jugar), de_la_plantilla.prefiere_temprano
    else:
        encontrado = re.fullmatch(r"sub (\d{1,2})(?: .*)?", nombre, re.IGNORECASE)
        if encontrado is None:
            raise NoSePuede("El nombre empieza con «Sub» y la edad, como «Sub 9».")
        edad, anios = int(encontrado.group(1)), 1
        genero = "F" if "femenino" in nombre.casefold() else "mixto"
        dias, temprano = [], False

    base = nivel_de_la_plantilla
    modalidad = (
        modalidad or (base.modalidad if base else "") or (hermana.modalidad if hermana else "")
    )
    min_por_tiempo = (
        min_por_tiempo
        or (base.min_por_tiempo if base else None)
        or (hermana.min_por_tiempo if hermana else None)
    )
    minimo = minimo or (base.min if base else None) or (hermana.min_jugadores if hermana else None)
    maximo = maximo or (base.max if base else None) or (hermana.max_jugadores if hermana else None)
    if not (modalidad and min_por_tiempo and minimo and maximo):
        raise NoSePuede("Completa la modalidad, los minutos por tiempo y el plantel.")
    if maximo < minimo:
        raise NoSePuede("El máximo de jugadores no puede ser menor que el mínimo.")

    nueva = CategoriaNivel.objects.create(
        torneo=torneo,
        categoria=nombre,
        nivel=nivel,
        edad=edad,
        anios_nacimiento=anios,
        genero=genero,
        modalidad=modalidad,
        min_jugadores=minimo,
        max_jugadores=maximo,
        min_por_tiempo=min_por_tiempo,
        convocados_por_partido=base.convocados_por_partido if base else None,
        dias_sin_jugar=dias,
        prefiere_temprano=temprano,
    )
    como_la_plantilla = base is not None and base.modalidad == modalidad
    nueva.canchas.set(_canchas(torneo, plantilla if como_la_plantilla else None, nueva))
    return nueva


def _canchas(torneo: Torneo, plantilla: ConfigTorneo | None, nueva: CategoriaNivel) -> list[Cancha]:
    existentes = {c.codigo: c for c in torneo.canchas.all()}
    codigos = canchas_compatibles(plantilla, nueva.categoria, nueva.nivel) if plantilla else ()
    if codigos and all(c in existentes for c in codigos):
        return [existentes[c] for c in codigos]
    igual = (
        torneo.categorias.filter(modalidad=nueva.modalidad)
        .exclude(pk=nueva.pk)
        .prefetch_related("canchas")
        .first()
    )
    return list(igual.canchas.all()) if igual else []
