"""Canchas flexibles (T10.5; P13, P63): agregar canchas, partirlas en mitades y unirlas.

Una cancha entera ocupa sus mitades: el programador y el verificador lo saben por `padre`.
En qué canchas juega cada categoría se elige en sus ajustes.
"""

import re

from django.db import transaction

from torneo.models import Cancha, Partido, Torneo


class NoSePuede(ValueError):
    """La acción no vale para esa cancha; el mensaje dice por qué."""


def agregar_cancha(torneo: Torneo) -> Cancha:
    numeros = [
        int(m.group(1))
        for codigo in Cancha.objects.filter(torneo=torneo, padre__isnull=True).values_list(
            "codigo", flat=True
        )
        if (m := re.fullmatch(r"C(\d+)", codigo))
    ]
    numero = max(numeros, default=0) + 1
    return Cancha.objects.create(torneo=torneo, codigo=f"C{numero}", nombre=f"Cancha {numero}")


@transaction.atomic
def partir(cancha: Cancha) -> list[Cancha]:
    if cancha.padre is not None:
        raise NoSePuede(f"{cancha.nombre} ya es una mitad.")
    if cancha.mitades.exists():
        raise NoSePuede(f"{cancha.nombre} ya está partida.")
    return [
        Cancha.objects.create(
            torneo=cancha.torneo,
            codigo=f"{cancha.codigo}{letra}",
            nombre=f"{cancha.nombre} {letra}",
            padre=cancha,
        )
        for letra in "AB"
    ]


def _con_partidos(canchas: list[Cancha]) -> bool:
    return Partido.objects.filter(cancha__in=canchas).exists()


@transaction.atomic
def unir(cancha: Cancha) -> None:
    mitades = list(cancha.mitades.all())
    if _con_partidos(mitades):
        raise NoSePuede(
            f"Una mitad de {cancha.nombre} tiene partidos: muévelos antes de unir la cancha."
        )
    for mitad in mitades:
        mitad.delete()


@transaction.atomic
def quitar(cancha: Cancha) -> None:
    if _con_partidos([cancha, *cancha.mitades.all()]):
        raise NoSePuede(f"{cancha.nombre} tiene partidos: muévelos antes de quitarla.")
    cancha.delete()
