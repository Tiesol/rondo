"""Carga la configuración de un torneo desde un JSON, como datos/config/jmp_cup_2026.json."""

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from pydantic import ValidationError

from dominio.config import cargar_config
from torneo.servicios.configuracion import cargar_configuracion


class Command(BaseCommand):
    help = (
        "Crea o actualiza un torneo desde su configuración en JSON. Se puede correr varias veces."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("archivo", type=Path)

    def handle(self, *args: Any, **opciones: Any) -> None:
        archivo: Path = opciones["archivo"]
        if not archivo.is_file():
            raise CommandError(f"No existe el archivo {archivo}.")
        try:
            config = cargar_config(archivo)
        except ValidationError as error:
            detalle = "\n".join(
                f"  - {'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in error.errors()
            )
            raise CommandError(f"La configuración no es válida:\n{detalle}") from None

        torneo = cargar_configuracion(config)
        self.stdout.write(
            self.style.SUCCESS(
                f"{torneo.nombre}: {torneo.categorias.count()} categorías-nivel, "
                f"{torneo.canchas.count()} canchas y {torneo.franjas.count()} franjas."
            )
        )
