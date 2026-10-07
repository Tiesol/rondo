"""Carga el catálogo de clubes (solo nombres y alias). Se puede correr varias veces."""

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from torneo.models import Club


class Command(BaseCommand):
    help = "Crea o actualiza los clubes del catálogo, con sus alias."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "archivo", nargs="?", type=Path, default=settings.RAIZ / "datos/config/clubes.json"
        )

    @transaction.atomic
    def handle(self, *args: Any, **opciones: Any) -> None:
        clubes: dict[str, list[str]] = json.loads(opciones["archivo"].read_text())["clubes"]
        for nombre, alias in clubes.items():
            club = Club.objects.filter(nombre__iexact=nombre).first() or Club(nombre=nombre)
            club.alias = sorted({*club.alias, *alias})
            club.full_clean()
            club.save()
        self.stdout.write(self.style.SUCCESS(f"{len(clubes)} clubes en el catálogo."))
