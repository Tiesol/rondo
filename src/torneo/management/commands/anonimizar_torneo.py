"""Borra los datos personales de un torneo terminado (P49). Solo con --confirmo."""

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from torneo.models import Torneo
from torneo.servicios.retencion import NoSePuedeAnonimizar, anonimizar


class Command(BaseCommand):
    help = (
        "Deja un torneo terminado sin nombres, documentos ni fechas de nacimiento. "
        "No se puede deshacer."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("torneo", type=int)
        parser.add_argument("--confirmo", action="store_true", help="No se puede deshacer.")

    def handle(self, *args: Any, **opciones: Any) -> None:
        torneo = Torneo.objects.filter(pk=opciones["torneo"]).first()
        if torneo is None:
            raise CommandError("No existe ese torneo.")
        if not opciones["confirmo"]:
            self.stdout.write(
                f"No hice nada. Esto borra para siempre los datos personales de {torneo}: "
                "córrelo con --confirmo."
            )
            return
        try:
            cantidad = anonimizar(torneo)
        except NoSePuedeAnonimizar as error:
            raise CommandError(str(error)) from None
        self.stdout.write(self.style.SUCCESS(f"{cantidad} personas quedaron sin datos personales."))
