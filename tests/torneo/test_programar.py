"""T3.7: la capacidad se ve antes de programar, solo para la organización."""

import io

import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import Client

from torneo.models import Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.capacidad import capacidad_del_torneo
from torneo.servicios.fixture import generar_fixtures_faltantes


@pytest.fixture
def demo(db: None) -> Torneo:
    call_command("generar_demo", "--soy-la-demo", stdout=io.StringIO())
    return Torneo.objects.get(es_demo=True)


def entrar(client: Client, grupo: str) -> Client:
    usuario = User.objects.create_user(grupo[:4], password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


def test_la_demo_tiene_dos_grupos_de_canchas(demo: Torneo) -> None:
    generar_fixtures_faltantes(demo)
    capacidad = capacidad_del_torneo(demo)
    assert [g.canchas for g in capacidad.total] == [("C1", "C2"), ("C3",)]
    assert capacidad.estimadas == []
    assert all(g.pedido > 0 for g in capacidad.eliminacion)
    assert capacidad.fines_de_semana == 5


def test_sin_fixture_se_estima_con_el_formato(demo: Torneo) -> None:
    capacidad = capacidad_del_torneo(demo)
    assert "Sub 6" in capacidad.estimadas
    generar_fixtures_faltantes(demo)
    con_fixture = capacidad_del_torneo(demo)
    assert [g.pedido for g in con_fixture.total] == [g.pedido for g in capacidad.total]


def test_la_pantalla_muestra_si_entra(client: Client, demo: Torneo) -> None:
    html = entrar(client, ORGANIZACION).get(f"/torneos/{demo.pk}/programar/").content.decode()
    assert "¿Entra todo?" in html
    assert "C1 y C2 · todo el torneo" in html
    assert "C3 · eliminación, desde el fin de semana 5" in html
    assert 'class="barra-cap"' in html


def test_la_mesa_no_programa(client: Client, demo: Torneo) -> None:
    respuesta = entrar(client, MESA).get(f"/torneos/{demo.pk}/programar/")
    assert respuesta.status_code == 403
    assert "Solo la organización puede programar" in respuesta.content.decode()
