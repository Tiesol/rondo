"""Arma la demo con datos inventados (T2.7). Solo con --soy-la-demo, y nunca sobre datos reales."""

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from torneo.models import Equipo, Jugador, Profe


class Command(BaseCommand):
    help = (
        "Genera un torneo de demo del tamaño de 2023, con jugadores inventados. "
        "Se niega si la base tiene datos que no son de demo. Se puede correr varias veces."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--soy-la-demo",
            action="store_true",
            help="Confirma que esta base es la de demo: borra y rehace los datos de demo.",
        )

    def handle(self, *args: Any, **opciones: Any) -> None:
        if not opciones["soy_la_demo"]:
            self.stdout.write(
                "No hice nada. Este comando borra y rehace los datos de demo: "
                "córrelo con --soy-la-demo, y solo contra la base de la demo."
            )
            return
        # faker es una dependencia de desarrollo: se importa recién acá.
        from torneo.servicios.demo import NoEsLaDemo, generar_demo

        try:
            torneo = generar_demo()
        except NoEsLaDemo as error:
            raise CommandError(f"{error} No toqué nada.") from None
        equipos = Equipo.objects.filter(categoria__torneo=torneo)
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo lista: {equipos.count()} equipos, "
                f"{Jugador.objects.filter(equipo__in=equipos).count()} jugadores y "
                f"{Profe.objects.filter(equipo__in=equipos).count()} profes, todos inventados."
            )
        )
