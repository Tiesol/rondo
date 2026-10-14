"""T4.7: el torneo de demo (unos 90 equipos) queda programado sin choques duros.

Tarda: programa los 223 partidos de la demo con el solver real. Corre con `pytest -m lento`.
"""

import io
import itertools
from collections.abc import Callable
from typing import Any

import pytest
from django.core.management import call_command

from torneo.models import Corrida, Partido, Torneo
from torneo.servicios.fixture import generar_fixtures_faltantes
from torneo.servicios.programador import programar_torneo


@pytest.mark.lento
@pytest.mark.django_db
def test_la_demo_queda_programada_sin_choques(
    settings: Any, agregar_jueves: Callable[[Any], None]
) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 90
    call_command("generar_demo", "--soy-la-demo", stdout=io.StringIO())
    torneo = Torneo.objects.get(es_demo=True)
    agregar_jueves(torneo)  # con F11 (P60) la cancha 3 no alcanza sin días extra (H8)
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


@pytest.mark.lento
@pytest.mark.django_db
def test_fase_12_bloque_a_en_la_demo_con_jueves(
    settings: Any, agregar_jueves: Callable[[Any], None]
) -> None:
    """A1 a A4 sobre la demo: el máximo por día con llaves, el orden de fechas, Sub 5 y Sub 6
    solo de fin de semana y el tiempo agregado solo para lo que no entra."""
    from collections import defaultdict

    from django.utils import timezone

    settings.PROGRAMADOR_SEGUNDOS = 90
    call_command("generar_demo", "--soy-la-demo", stdout=io.StringIO())
    torneo = Torneo.objects.get(es_demo=True)
    agregar_jueves(torneo)
    generar_fixtures_faltantes(torneo)
    corrida = programar_torneo(torneo)
    assert corrida.resultado["sin_ubicar"] == []
    assert corrida.resultado["choques"] == {}  # incluye A1: grupos más llaves por día

    partidos = list(
        Partido.objects.filter(categoria__torneo=torneo).select_related("categoria", "cancha")
    )
    # A3: Sub 5 y Sub 6 solo sábado y domingo.
    for p in partidos:
        if p.categoria.categoria in ("Sub 5", "Sub 6"):
            assert timezone.localtime(p.inicio).weekday() in (5, 6), p
    # A4: el jueves es solo para lo que no entra en el horario normal: F11 en la cancha 3.
    del_jueves = [p for p in partidos if timezone.localtime(p.inicio).weekday() == 3]
    assert all(p.categoria.modalidad == "F11" for p in del_jueves), [
        (str(p.categoria), p.cancha) for p in del_jueves if p.categoria.modalidad != "F11"
    ]
    # A2: con lugar, ninguna fecha de grupos queda al revés.
    por_equipo: dict[int, list[Partido]] = defaultdict(list)
    for p in partidos:
        if p.fase == "grupos":
            for e in (p.local_id, p.visitante_id):
                if e is not None:
                    por_equipo[e].append(p)
    al_reves = 0
    for suyos in por_equipo.values():
        suyos.sort(key=lambda p: p.fecha or 0)
        for antes, despues in itertools.pairwise(suyos):
            assert antes.inicio is not None and despues.inicio is not None
            if despues.inicio < antes.inicio:
                al_reves += 1
    assert al_reves == 0, f"{al_reves} fechas al revés"
    # B5: la lista de intercambios carga rápido aun con los 223 partidos.
    import time

    from torneo.servicios.reprogramar import candidatos_de_intercambio

    elegido = next(
        p
        for p in partidos
        if p.categoria.modalidad == "F7" and p.inicio and p.local_id and p.visitante_id
    )
    comienzo = time.monotonic()
    candidatos = candidatos_de_intercambio(elegido)
    assert time.monotonic() - comienzo < 6, "la lista de intercambios tarda demasiado"
    assert candidatos
