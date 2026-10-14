"""T3.7: la capacidad se ve antes de programar, solo para la organización."""

import io
from collections.abc import Callable
from typing import Any

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
    assert capacidad.fines_de_semana == 4


def test_sin_fixture_se_estima_con_el_formato(demo: Torneo) -> None:
    capacidad = capacidad_del_torneo(demo)
    assert "Sub 6" in capacidad.estimadas
    generar_fixtures_faltantes(demo)
    con_fixture = capacidad_del_torneo(demo)
    assert [g.pedido for g in con_fixture.total] == [g.pedido for g in capacidad.total]


def test_la_pantalla_muestra_si_entra(client: Client, demo: Torneo) -> None:
    html = entrar(client, ORGANIZACION).get(f"/torneos/{demo.pk}/programar/").content.decode()
    assert "¿Entra todo?" in html
    assert "C1 y C2" in html
    assert "eliminación, desde" not in html  # T11.4: el fin de semana es solo sugerido
    assert 'class="barra-cap"' in html


def test_t11_4_si_no_entra_dice_cuanto_falta_y_que_hacer(client: Client, demo: Torneo) -> None:
    generar_fixtures_faltantes(demo)
    assert not all(g.entra for g in capacidad_del_torneo(demo).total)  # F11 en C3 (H8)
    html = entrar(client, ORGANIZACION).get(f"/torneos/{demo.pk}/programar/").content.decode()
    assert "Faltan" in html
    assert "Agrega un día" in html


def test_la_mesa_no_programa(client: Client, demo: Torneo) -> None:
    respuesta = entrar(client, MESA).get(f"/torneos/{demo.pk}/programar/")
    assert respuesta.status_code == 403
    assert "Solo la organización puede programar" in respuesta.content.decode()


def test_a5_el_ultimo_inicio_a_la_hora_de_cierre_suma_un_partido_por_franja(demo: Torneo) -> None:
    # P48: el último partido de cada franja puede empezar a la hora de cierre. Sin jueves,
    # C3 (F11) pedía 18 h de más; al programar quedan unas 6 h sin lugar.
    generar_fixtures_faltantes(demo)
    c3 = next(g for g in capacidad_del_torneo(demo).total if g.canchas == ("C3",))
    assert 5 * 60 <= c3.faltan <= 7 * 60


def test_a5_con_tiempo_agregado_dice_que_entra_usandolo(
    demo: Torneo, agregar_jueves: Callable[[Any], None]
) -> None:
    generar_fixtures_faltantes(demo)
    agregar_jueves(demo)
    capacidad = capacidad_del_torneo(demo)
    c3 = next(g for g in capacidad.total if g.canchas == ("C3",))
    c3_con = next(g for g in capacidad.con_extra if g.canchas == ("C3",))
    assert not c3.entra  # con el horario normal, no
    assert c3_con.entra  # con los jueves, sí


def test_a5_la_pantalla_dice_que_hace_falta_el_tiempo_agregado(
    client: Client,
    demo: Torneo,
    agregar_jueves: Callable[[Any], None],
) -> None:
    generar_fixtures_faltantes(demo)
    agregar_jueves(demo)
    html = entrar(client, ORGANIZACION).get(f"/torneos/{demo.pk}/programar/").content.decode()
    assert "Entra usando el tiempo agregado" in html


def test_el_tiempo_maximo_sale_de_la_configuracion(
    client: Client, demo: Torneo, settings: Any
) -> None:
    org = entrar(client, ORGANIZACION)
    settings.PROGRAMADOR_SEGUNDOS = 120
    assert "hasta 2 minutos" in org.get(f"/torneos/{demo.pk}/programar/").content.decode()
    settings.PROGRAMADOR_SEGUNDOS = 60
    assert "hasta 1 minuto." in org.get(f"/torneos/{demo.pk}/programar/").content.decode()
