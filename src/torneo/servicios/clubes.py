"""Catálogo de clubes desde un JSON (solo nombres y alias)."""

import json
from pathlib import Path

from django.db import transaction

from torneo.models import Club, EquipoDeClub


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
def unir_clubes(repetido: Club, destino: Club) -> list[str]:
    """Pasa los equipos de `repetido` a `destino`, que se queda con su nombre como alias, y borra
    `repetido` (T13.1). Un equipo con el mismo nombre en los dos se une en uno, con el escudo
    de `destino` (o el otro, si `destino` no tenía). Devuelve los nombres de los equipos unidos,
    para avisar."""
    if repetido.pk == destino.pk:
        raise NoSePuede("Elige otro club.")
    unidos: list[str] = []
    sobrantes: list[str] = []
    for del_club in repetido.equipos_del_club.prefetch_related("equipos__categoria"):
        igual = destino.equipos_del_club.filter(nombre__iexact=del_club.nombre).first()
        if igual is None:
            del_club.club = destino
            del_club.save(update_fields=["club"])
            del_club.equipos.update(club=destino)
            continue
        for equipo in del_club.equipos.all():
            if igual.equipos.filter(categoria=equipo.categoria).exists():
                raise NoSePuede(
                    f"Los dos tienen un equipo «{igual.nombre}» en {equipo.categoria}: "
                    "cámbiale el nombre a uno antes de unirlos."
                )
        del_club.equipos.update(equipo_de_club=igual, club=destino, nombre=igual.nombre)
        if not igual.escudo and del_club.escudo:
            igual.escudo = del_club.escudo.name
            igual.save(update_fields=["escudo"])
        elif del_club.escudo.name:
            sobrantes.append(del_club.escudo.name)
        del_club.delete()
        unidos.append(igual.nombre)
    destino.alias = _alias(
        "\n".join([repetido.nombre, *repetido.alias, *destino.alias]), destino.nombre
    )
    destino.save(update_fields=["alias"])
    repetido.delete()
    borrar_si_nadie_los_usa(sobrantes)
    return unidos


def borrar_si_nadie_los_usa(archivos: list[str]) -> None:
    """Borra, al confirmar, los escudos que ya no usa ningún equipo (pueden estar compartidos)."""
    libres = [a for a in archivos if not EquipoDeClub.objects.filter(escudo=a).exists()]
    if libres:
        storage = EquipoDeClub().escudo.storage

        def borrar() -> None:
            for archivo in libres:
                storage.delete(archivo)

        transaction.on_commit(borrar)


@transaction.atomic
def borrar_club(club: Club) -> None:
    """T13.3: solo si no tiene equipos en ningún torneo. Sus equipos del club sin categorías se
    borran con él."""
    equipos = list(club.equipos.select_related("categoria__torneo")[:3])
    if equipos:
        donde = ", ".join(f"{e.nombre} en {e.categoria}" for e in equipos)
        raise NoSePuede(
            f"{club} tiene equipos inscritos ({donde}): bórralos o pásalos a otro club antes."
        )
    escudos = [d.escudo.name for d in club.equipos_del_club.all() if d.escudo.name]
    club.equipos_del_club.all().delete()
    club.delete()
    borrar_si_nadie_los_usa(escudos)
