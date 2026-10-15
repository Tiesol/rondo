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


@pytest.mark.lento
@pytest.mark.django_db
def test_t13_8_f11_entra_ampliando_c3_los_fines_de_semana_sin_jueves(settings: Any) -> None:
    """P79: sin jueves ni otra cancha. Con el tiempo que sugiere "¿Entra todo?", antes de las
    8 en C3 los sábados y domingos, entra todo y no hay partidos en jueves."""
    from datetime import datetime, time, timedelta

    from django.utils import timezone

    from torneo.models import Franja
    from torneo.servicios.capacidad import capacidad_del_torneo
    from torneo.views.calendario import dias_de_fin_de_semana
    from torneo.views.programar import minutos_por_dia

    settings.PROGRAMADOR_SEGUNDOS = 90
    call_command("generar_demo", "--soy-la-demo", stdout=io.StringIO())
    torneo = Torneo.objects.get(es_demo=True)
    generar_fixtures_faltantes(torneo)
    (c3,) = [g for g in capacidad_del_torneo(torneo).total if not g.entra]
    dias = dias_de_fin_de_semana(torneo)
    por_dia = minutos_por_dia(c3.faltan, len(dias))  # lo que sugiere la pantalla
    cancha = torneo.canchas.get(codigo="C3")
    for dia in dias:
        ocho = timezone.make_aware(datetime.combine(dia, time(8)))
        franja = Franja.objects.create(
            torneo=torneo,
            inicio=ocho - timedelta(minutes=por_dia),
            fin=ocho,
            tipo=Franja.Tipo.ENTRE_SEMANA,
        )
        franja.canchas.set([cancha])
    assert all(g.entra for g in capacidad_del_torneo(torneo).con_extra)

    corrida = programar_torneo(torneo)

    assert corrida.resultado["sin_ubicar"] == []
    assert corrida.resultado["choques"] == {}
    partidos = Partido.objects.filter(categoria__torneo=torneo).select_related("categoria")
    assert not [p for p in partidos if timezone.localtime(p.inicio).weekday() == 3]

    # T13.17: los horarios libres sugeridos salen rápido aun con los 223 partidos.
    import time as reloj

    from torneo.servicios.sugerencias import horarios_libres

    elegido = (
        Partido.objects.filter(categoria__torneo=torneo, categoria__modalidad="F7")
        .select_related("categoria__torneo", "cancha", "local", "visitante")
        .order_by("inicio")
        .first()
    )
    assert elegido is not None and elegido.inicio is not None
    comienzo = reloj.monotonic()
    libres, _ = horarios_libres(elegido, ahora=elegido.inicio - timedelta(days=1))
    assert reloj.monotonic() - comienzo < 1.5, "los horarios sugeridos tardan demasiado"
    assert libres
