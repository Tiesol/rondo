"""T4.7: el torneo de demo (unos 90 equipos) queda programado sin choques duros.

Tarda: programa los 223 partidos de la demo con el solver real. Corre con `pytest -m lento`.
"""

import io
from typing import Any

import pytest
from django.core.management import call_command

from torneo.models import Corrida, Partido, Torneo
from torneo.servicios.fixture import generar_fixtures_faltantes
from torneo.servicios.programador import programar_torneo


@pytest.mark.lento
@pytest.mark.django_db
def test_la_demo_queda_programada_sin_choques(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 90
    call_command("generar_demo", "--soy-la-demo", stdout=io.StringIO())
    torneo = Torneo.objects.get(es_demo=True)
    generar_fixtures_faltantes(torneo)

    corrida = programar_torneo(torneo)

    assert corrida.estado == Corrida.Estado.TERMINADA
    assert corrida.resultado["choques"] == {}, "el verificador encontró choques duros"
    total = Partido.objects.filter(categoria__torneo=torneo).count()
    assert corrida.resultado["total"] == total
    sin_ubicar = corrida.resultado["sin_ubicar"]
    assert corrida.resultado["ubicados"] + len(sin_ubicar) == total
    assert all(s["motivo"] for s in sin_ubicar), "todo lo que no entra tiene motivo"
    # Con la configuración 2026 y la demo, entra todo (T4.6: 223 de 223).
    assert sin_ubicar == []
