"""T13.18: las propuestas mueven solo lo que choca. Las alternativas son otros horarios u otros
días para esos mismos partidos (no se completan moviendo de más), y cada movimiento dice por
qué. Caso de la prueba de Sebastian: un bloqueo de un equipo que choca con un solo partido.
Datos inventados."""

from datetime import datetime, timedelta
from typing import Any

import pytest
from django.conf import settings
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import Bloqueo, CategoriaNivel, Club, Equipo, Partido, Torneo
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo
from torneo.servicios.reprogramar import calcular_propuestas


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 15


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    for categoria in ("Sub 9", "Sub 10"):
        cn: CategoriaNivel = torneo.categorias.get(categoria=categoria, nivel="inicial")
        for i in range(4):
            club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
            Equipo.objects.create(club=club, categoria=cn, nombre=f"{categoria} {i}")
        generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    return torneo


@pytest.mark.django_db
def test_las_propuestas_mueven_solo_el_que_choca_y_dicen_por_que(torneo: Torneo) -> None:
    partido = Partido.objects.filter(inicio__isnull=False).order_by("inicio").first()
    assert partido is not None and partido.inicio is not None and partido.local is not None
    bloqueo = Bloqueo.objects.create(
        torneo=torneo,
        inicio=partido.inicio - timedelta(minutes=10),
        fin=partido.inicio + timedelta(minutes=20),
        motivo="Partido de la ACF",
    )
    bloqueo.equipos.set([partido.local])
    corrida = calcular_propuestas(bloqueo)
    propuestas = corrida.resultado["propuestas"]
    assert propuestas, "hay al menos una forma de mover el partido que choca"
    for propuesta in propuestas:
        assert [m["partido"] for m in propuesta] == [partido.pk], "no mueve de más"
        assert "Choca" in propuesta[0]["motivo"]
    # Las alternativas son horarios de verdad distintos (no 5 minutos más tarde).
    turno = timedelta(minutes=partido.categoria.minutos_turno)
    inicios = [datetime.fromisoformat(p[0]["despues"][1]) for p in propuestas]
    for i, uno in enumerate(inicios):
        for otro in inicios[i + 1 :]:
            assert abs(uno - otro) >= turno, (uno, otro)
    assert timezone.is_aware(partido.inicio)
