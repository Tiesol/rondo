"""Carga el catálogo de clubes (solo nombres y alias). Se puede correr varias veces."""

from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from torneo.servicios.clubes import cargar_clubes


class Command(BaseCommand):
    help = "Crea o actualiza los clubes del catálogo, con sus alias."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("archivo", nargs="?", type=Path, default=settings.CATALOGO_CLUBES)

    def handle(self, *args: Any, **opciones: Any) -> None:
        cantidad = cargar_clubes(opciones["archivo"])
        self.stdout.write(self.style.SUCCESS(f"{cantidad} clubes en el catálogo."))
