"""T5.7: el calendario por club y por categoría. Datos inventados."""

from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Partido, Torneo
from torneo.permisos import MESA
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10
    settings.PROGRAMADOR_TRABAJADORES = 4


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    river = Club.objects.create(nombre="River Plate")
    for categoria in ("Sub 9", "Sub 11"):
        cn = torneo.categorias.get(categoria=categoria, nivel="avanzado")
        Equipo.objects.create(club=river, categoria=cn, nombre="River Plate")
        for i in range(3):
            club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
            Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}")
        generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    return torneo


def mesa(client: Client) -> Client:
    usuario = User.objects.create_user("mesa", password="x")
    usuario.groups.add(Group.objects.get(name=MESA))
    client.force_login(usuario)
    return client


@pytest.mark.django_db
def test_por_club_todos_los_partidos_de_sus_equipos_en_orden(
    client: Client, torneo: Torneo
) -> None:
    river = Club.objects.get(nombre="River Plate")
    html = mesa(client).get(f"/calendario/club/{river.pk}/").content.decode()
    suyos = (
        (Partido.objects.filter(local__club=river) | Partido.objects.filter(visitante__club=river))
        .filter(inicio__isnull=False)
        .order_by("inicio")
    )
    assert suyos.count() == 6  # 3 por categoría
    horas = [f"{timezone.localtime(p.inicio):%H:%M}" for p in suyos if p.inicio]
    posiciones = []
    inicio = 0
    for hora in horas:
        inicio = html.index(hora, inicio)
        posiciones.append(inicio)
    assert posiciones == sorted(posiciones)
    assert "Sub 9 Avanzado" in html and "Sub 11 Avanzado" in html


@pytest.mark.django_db
def test_el_calendario_ofrece_elegir_un_club(client: Client, torneo: Torneo) -> None:
    con_sesion = mesa(client)
    club = Club.objects.first()
    assert club is not None
    respuesta = con_sesion.get("/calendario/club/", {"club": club.pk})
    assert respuesta["Location"] == f"/calendario/club/{club.pk}/"
    html = con_sesion.get("/calendario/", follow=True).content.decode()
    assert 'action="/calendario/club/"' in html


@pytest.mark.django_db
def test_por_categoria_el_fixture_muestra_los_partidos_en_orden(
    client: Client, torneo: Torneo
) -> None:
    sub9 = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    html = mesa(client).get(f"/torneo/{sub9.pk}/fixture/").content.decode()
    fecha_1 = Partido.objects.filter(categoria=sub9, fecha=1).first()
    assert fecha_1 is not None and fecha_1.inicio is not None
    assert f"{timezone.localtime(fecha_1.inicio):%H:%M}" in html
