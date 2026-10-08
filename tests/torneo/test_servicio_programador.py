"""T4.5: corrida y servicio de programación. Datos inventados."""

from datetime import timedelta
from typing import Any

import pytest
from django.conf import settings
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Corrida, Equipo, Partido, Torneo
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import ProgramacionEnCurso, programar_torneo


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10
    settings.PROGRAMADOR_TRABAJADORES = 4


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    for categoria, nivel in (("Sub 9", "avanzado"), ("Sub 6", "unico")):
        cn: CategoriaNivel = torneo.categorias.get(categoria=categoria, nivel=nivel)
        for i in range(4):
            club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
            Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}")
        generar_fixture(cn, semilla=1)
    return torneo


@pytest.mark.django_db
def test_programa_el_torneo_y_guarda_la_corrida(torneo: Torneo) -> None:
    corrida = programar_torneo(torneo)
    assert corrida.estado == Corrida.Estado.TERMINADA
    total = Partido.objects.filter(categoria__torneo=torneo).count()
    assert corrida.resultado["total"] == total == 20
    assert corrida.resultado["ubicados"] == total
    assert corrida.resultado["sin_ubicar"] == []
    assert corrida.resultado["choques"] == {}
    franjas = list(torneo.franjas.all())
    for partido in Partido.objects.filter(categoria__torneo=torneo).select_related("cancha"):
        assert partido.estado == Partido.Estado.PROGRAMADO
        assert partido.cancha is not None and partido.inicio is not None
        assert any(f.inicio <= partido.inicio < f.fin for f in franjas)
    sub6 = Partido.objects.filter(categoria__categoria="Sub 6").select_related("cancha")
    assert {p.cancha.codigo for p in sub6 if p.cancha} <= {"C1A", "C1B"}


@pytest.mark.django_db
def test_no_se_programa_dos_veces_a_la_vez(torneo: Torneo) -> None:
    Corrida.objects.create(torneo=torneo, estado=Corrida.Estado.CORRIENDO)
    with pytest.raises(ProgramacionEnCurso):
        programar_torneo(torneo)


@pytest.mark.django_db
def test_una_corrida_colgada_no_bloquea_para_siempre(torneo: Torneo) -> None:
    vieja = Corrida.objects.create(torneo=torneo, estado=Corrida.Estado.CORRIENDO)
    Corrida.objects.filter(pk=vieja.pk).update(inicio=timezone.now() - timedelta(hours=1))
    assert programar_torneo(torneo).estado == Corrida.Estado.TERMINADA


@pytest.mark.django_db
def test_los_jugados_y_fijados_no_cambian(torneo: Torneo) -> None:
    programar_torneo(torneo)
    jugado, fijado = Partido.objects.filter(categoria__categoria="Sub 9", fase="grupos")[:2]
    jugado.estado = Partido.Estado.JUGADO
    jugado.save()
    fijado.fijado = True
    fijado.save()
    antes = {p.pk: (p.cancha_id, p.inicio) for p in (jugado, fijado)}
    programar_torneo(torneo)
    for partido in Partido.objects.filter(pk__in=antes):
        assert (partido.cancha_id, partido.inicio) == antes[partido.pk]
    assert Partido.objects.get(pk=jugado.pk).estado == Partido.Estado.JUGADO


@pytest.mark.django_db
def test_lo_que_no_entra_queda_con_su_motivo(torneo: Torneo) -> None:
    sub6 = torneo.categorias.get(categoria="Sub 6")
    sub6.canchas.clear()
    corrida = programar_torneo(torneo)
    sin_ubicar = corrida.resultado["sin_ubicar"]
    assert len(sin_ubicar) == 10
    assert all(s["motivo"] == "No tiene canchas compatibles" for s in sin_ubicar)
    assert all("Sub 6" in s["partido"] for s in sin_ubicar)
    assert not Partido.objects.filter(categoria=sub6, cancha__isnull=False).exists()
    assert set(Partido.objects.filter(categoria=sub6).values_list("estado", flat=True)) == {
        "pendiente"
    }
