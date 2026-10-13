"""Catálogo de clubes desde un JSON (solo nombres y alias)."""

import json
from pathlib import Path

from django.db import transaction

from torneo.models import Club


@transaction.atomic
def cargar_clubes(archivo: Path) -> int:
    """Crea o actualiza los clubes, sumando alias sin borrar los que ya tenían."""
    clubes: dict[str, list[str]] = json.loads(archivo.read_text())["clubes"]
    for nombre, alias in clubes.items():
        club = Club.objects.filter(nombre__iexact=nombre).first() or Club(nombre=nombre)
        club.alias = sorted({*club.alias, *alias})
        club.full_clean()
        club.save()
    return len(clubes)


class NoSePuede(ValueError):
    """La acción no vale; el mensaje dice por qué."""


def _alias(texto: str, nombre: str) -> list[str]:
    """Uno por línea, sin repetidos ni el nombre mismo."""
    vistos = {nombre.strip().casefold()}
    alias = []
    for linea in texto.splitlines():
        if (limpio := linea.strip()) and limpio.casefold() not in vistos:
            vistos.add(limpio.casefold())
            alias.append(limpio)
    return sorted(alias)


def _nombre_libre(nombre: str, menos: Club | None = None) -> str:
    nombre = nombre.strip()
    if not nombre:
        raise NoSePuede("Escribe el nombre del club.")
    otros = Club.objects.filter(nombre__iexact=nombre)
    if menos is not None:
        otros = otros.exclude(pk=menos.pk)
    if otros.exists():
        raise NoSePuede(f"Ya hay un club llamado {nombre}.")
    return nombre


def crear_club(nombre: str, alias: str) -> Club:
    """T11.6 (P10): los clubes los carga la organización."""
    nombre = _nombre_libre(nombre)
    return Club.objects.create(nombre=nombre, alias=_alias(alias, nombre))


def editar_club(club: Club, nombre: str, alias: str) -> None:
    club.nombre = _nombre_libre(nombre, menos=club)
    club.alias = _alias(alias, club.nombre)
    club.save(update_fields=["nombre", "alias"])


@transaction.atomic
def unir_clubes(repetido: Club, destino: Club) -> None:
    """Pasa los equipos de `repetido` a `destino`, que se queda con su nombre como alias (y su
    escudo, si no tenía), y borra `repetido`."""
    if repetido.pk == destino.pk:
        raise NoSePuede("Elige otro club.")
    for equipo in repetido.equipos.select_related("categoria"):
        if destino.equipos.filter(categoria=equipo.categoria, nombre=equipo.nombre).exists():
            raise NoSePuede(
                f"Los dos tienen un equipo «{equipo.nombre}» en {equipo.categoria}: "
                "cámbiale el nombre a uno antes de unirlos."
            )
    repetido.equipos.update(club=destino)
    destino.alias = _alias(
        "\n".join([repetido.nombre, *repetido.alias, *destino.alias]), destino.nombre
    )
    campos = ["alias"]
    if not destino.escudo and repetido.escudo:
        destino.escudo, repetido.escudo = repetido.escudo.name, ""
        campos.append("escudo")
    destino.save(update_fields=campos)
    escudo_viejo = repetido.escudo.name if repetido.escudo else ""
    repetido.delete()
    if escudo_viejo:
        storage = destino.escudo.storage
        transaction.on_commit(lambda: storage.delete(escudo_viejo))
