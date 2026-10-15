"""Equipos del club: renombrar (T13.1). El nombre vive en EquipoDeClub; cada Equipo (una
categoría) guarda una copia, que se cambia acá y en la misma transacción."""

from django.db import transaction

from torneo.models import Equipo, EquipoDeClub
from torneo.servicios.clubes import NoSePuede


@transaction.atomic
def renombrar_equipo(del_club: EquipoDeClub, nombre: str) -> None:
    nombre = nombre.strip()
    if not nombre:
        raise NoSePuede("Escribe el nombre del equipo.")
    otros = EquipoDeClub.objects.filter(club_id=del_club.club_id, nombre__iexact=nombre)
    if otros.exclude(pk=del_club.pk).exists():
        raise NoSePuede(f"{del_club.club} ya tiene un equipo llamado {nombre}.")
    del_club.nombre = nombre
    del_club.save(update_fields=["nombre"])
    Equipo.objects.filter(equipo_de_club=del_club).update(nombre=nombre)
