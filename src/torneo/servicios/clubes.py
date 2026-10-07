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
