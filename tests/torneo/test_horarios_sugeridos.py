"""T13.17: en Mover, "Horarios libres sugeridos": los inicios posibles (cada franja en cada cancha
compatibles) que pasan el verificador, los más cercanos al horario actual primero. Datos
inventados."""

from datetime import timedelta
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Partido, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo
from torneo.servicios.reprogramar import mover_a_mano
from torneo.servicios.sugerencias import horarios_libres


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10


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


def primero() -> Partido:
    partido = (
        Partido.objects.filter(inicio__isnull=False)
        .select_related("categoria__torneo", "cancha", "local", "visitante")
        .order_by("inicio")
        .first()
    )
    assert partido is not None
    return partido


@pytest.mark.django_db
def test_los_sugeridos_no_tienen_choques_y_se_pueden_mover(torneo: Torneo) -> None:
    partido = primero()
    libres, _ = horarios_libres(partido, cuantos=5)
    assert 1 <= len(libres) <= 5
    ahora = (partido.cancha, partido.inicio)
    for s in libres:
        assert s.avisos == [] and (s.cancha, s.inicio) != ahora
        assert s.cancha in partido.categoria.canchas.all()
    # El primero se puede mover sin confirmar nada.
    mover_a_mano(partido, libres[0].cancha, libres[0].inicio)


@pytest.mark.django_db
def test_primero_los_del_mismo_dia(torneo: Torneo) -> None:
    partido = primero()
    libres, _ = horarios_libres(partido, cuantos=3)
    assert partido.inicio is not None
    dia = timezone.localtime(partido.inicio).date()
    assert timezone.localtime(libres[0].inicio).date() == dia


@pytest.mark.django_db
def test_nunca_en_el_pasado_ni_donde_la_cancha_esta_ocupada(torneo: Torneo) -> None:
    partido = primero()
    otros = [p for p in Partido.objects.filter(inicio__isnull=False).exclude(pk=partido.pk)]
    libres, con_avisos = horarios_libres(partido, cuantos=10, ahora=partido.inicio)
    for s in [*libres, *con_avisos]:
        assert s.inicio >= partido.inicio  # type: ignore[operator]
        fin = s.inicio + timedelta(minutes=partido.categoria.minutos_turno)
        for otro in otros:
            if otro.cancha_id == s.cancha.pk and otro.inicio is not None:
                fin_otro = otro.inicio + timedelta(minutes=otro.categoria.minutos_turno)
                assert fin <= otro.inicio or fin_otro <= s.inicio


@pytest.mark.django_db
def test_la_pantalla_mover_los_muestra_con_mover_aqui(client: Client, torneo: Torneo) -> None:
    partido = primero()
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    html = client.get(f"/partidos/{partido.pk}/mover/").content.decode()
    assert "Horarios libres sugeridos" in html and "Mover aquí" in html
