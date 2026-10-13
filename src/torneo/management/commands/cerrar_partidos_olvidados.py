"""T11.12: cierra los partidos olvidados de todos los torneos. Para un cron, si lo hay; si no,
la app lo hace sola al abrir Hoy, la ficha o la página pública."""

from typing import Any

from django.core.management.base import BaseCommand

from torneo.models import Torneo
from torneo.servicios.partido import cerrar_olvidados


class Command(BaseCommand):
    help = "Cierra los partidos que siguen en juego pasado su final esperado (P82)."

    def handle(self, *args: Any, **opciones: Any) -> None:
        cerrados = sum(cerrar_olvidados(torneo) for torneo in Torneo.objects.all())
        self.stdout.write(f"Partidos cerrados: {cerrados}")
