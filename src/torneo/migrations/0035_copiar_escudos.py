"""T13.1, paso 2 de 3: un equipo del club por cada club + nombre que ya existe, con el escudo
que tenía su club. No borra nada: el escudo del club se quita recién en el paso 3."""

from typing import Any

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def copiar(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Equipo: Any = apps.get_model("torneo", "Equipo")
    EquipoDeClub: Any = apps.get_model("torneo", "EquipoDeClub")
    vistos: set[tuple[int, int]] = set()
    for equipo in Equipo.objects.select_related("club").order_by("pk"):
        nombre = equipo.nombre.strip()
        del_club = EquipoDeClub.objects.filter(club=equipo.club, nombre__iexact=nombre).first()
        # Dos equipos del club en la misma categoría que solo difieren en mayúsculas: el segundo
        # pasa a ser otro equipo, para no romper la unicidad nueva (equipo del club, categoría).
        if del_club is not None and (del_club.pk, equipo.categoria_id) in vistos:
            nombre, del_club = f"{nombre} (2)", None
        if del_club is None:
            del_club = EquipoDeClub.objects.create(
                club=equipo.club, nombre=nombre, escudo=equipo.club.escudo
            )
        vistos.add((del_club.pk, equipo.categoria_id))
        equipo.equipo_de_club = del_club
        equipo.nombre = del_club.nombre
        equipo.save(update_fields=["equipo_de_club", "nombre"])


def devolver(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Al volver atrás, cada club recupera el escudo de alguno de sus equipos."""
    # Modelos históricos: el Club de acá todavía tiene escudo.
    Club: Any = apps.get_model("torneo", "Club")
    EquipoDeClub: Any = apps.get_model("torneo", "EquipoDeClub")
    for club in Club.objects.filter(escudo=""):
        con_escudo = EquipoDeClub.objects.filter(club=club).exclude(escudo="").first()
        if con_escudo is not None:
            club.escudo = con_escudo.escudo
            club.save(update_fields=["escudo"])


class Migration(migrations.Migration):

    dependencies = [
        ('torneo', '0034_equipo_de_club'),
    ]

    operations = [
        migrations.RunPython(copiar, devolver),
    ]
