"""T0.6: mide el solver con una instancia sintética del tamaño del torneo 2023."""

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from dominio.programador.espiga import Division, generar_instancia, resolver

# Las 14 divisiones de 2023 (sección 6.2): tipo de cancha y cantidad de equipos.
TORNEO_2023 = [
    Division("mitades", 3),  # Sub 5
    Division("mitades", 9),  # Sub 6
    Division("F7", 6),  # Sub 7
    Division("F7", 8),  # Sub 8 Inicial
    Division("F7", 5),  # Sub 8 Avanzado
    Division("F7", 6),  # Sub 9 Inicial
    Division("F7", 6),  # Sub 9 Avanzado
    Division("F7", 4),  # Sub 10 Inicial
    Division("F8", 5),  # Sub 10 Avanzado
    Division("F7", 4),  # Sub 11 Inicial
    Division("F8", 8),  # Sub 11 Avanzado
    Division("F11", 8),  # Sub 12
    Division("F11", 5),  # Sub 13
    Division("F11", 7),  # Sub 15
]


def _memoria_pico_mb() -> float | None:
    """Pico de memoria del contenedor (cgroup v2), si se corre dentro de uno."""
    pico = Path("/sys/fs/cgroup/memory.peak")
    return int(pico.read_text()) / 2**20 if pico.exists() else None


class Command(BaseCommand):
    help = "Mide OR-Tools CP-SAT con una instancia sintética del tamaño de 2023 (T0.6)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--segundos", type=float, default=60)
        parser.add_argument("--workers", type=int, default=1)
        parser.add_argument("--findes", type=int, default=4)
        parser.add_argument("--profes", type=int, default=18)

    def handle(self, *args: Any, **opciones: Any) -> None:
        instancia = generar_instancia(
            TORNEO_2023, opciones["findes"], opciones["profes"], semilla=2023
        )
        resultado = resolver(instancia, opciones["segundos"], opciones["workers"])
        primera = resultado.segundos_hasta_primera
        memoria = _memoria_pico_mb()
        self.stdout.write(
            f"partidos={len(instancia.partidos)} estado={resultado.estado} "
            f"primera_solucion={'-' if primera is None else f'{primera:.2f}s'} "
            f"total={resultado.segundos_totales:.1f}s workers={opciones['workers']} "
            f"memoria_pico={'-' if memoria is None else f'{memoria:.0f}MB'}"
        )
