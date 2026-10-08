"""T3.5: pantallas de series y fixture, y el fixture en la página pública."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    torneo.publico = True
    torneo.save()
    return torneo


def categoria_con(torneo: Torneo, cantidad: int, categoria: str = "Sub 9") -> CategoriaNivel:
    cn: CategoriaNivel = torneo.categorias.get(categoria=categoria, nivel="avanzado")
    for i in range(cantidad):
        club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
        Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}")
    return cn


def entrar(client: Client, grupo: str) -> Client:
    usuario = User.objects.create_user(grupo[:4], password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


@pytest.mark.django_db
def test_la_organizacion_genera_el_fixture_y_lo_ve_por_fecha(
    client: Client, torneo: Torneo
) -> None:
    cn = categoria_con(torneo, 6)
    org = entrar(client, ORGANIZACION)
    assert "Generar el fixture" in org.get(f"/torneo/{cn.pk}/fixture/").content.decode()
    respuesta = org.post(f"/torneo/{cn.pk}/fixture/generar/")
    assert respuesta["Location"] == f"/torneo/{cn.pk}/fixture/"
    html = org.get(f"/torneo/{cn.pk}/fixture/").content.decode()
    assert "Fecha 1" in html
    assert "Equipo 0" in html
    assert "Semi 1 de Oro" in html
    assert "1.º A" in html
    assert "Serie A" in html


@pytest.mark.django_db
def test_la_mesa_ve_el_fixture_pero_no_lo_genera(client: Client, torneo: Torneo) -> None:
    cn = categoria_con(torneo, 4)
    generar_fixture(cn)
    mesa = entrar(client, MESA)
    html = mesa.get(f"/torneo/{cn.pk}/fixture/").content.decode()
    assert "Fecha 1" in html
    assert "/fixture/generar/" not in html
    respuesta = mesa.post(f"/torneo/{cn.pk}/fixture/generar/")
    assert respuesta.status_code == 403
    assert "Solo la organización puede generar el fixture" in respuesta.content.decode()


@pytest.mark.django_db
def test_mover_equipos_de_serie_rehace_los_cruces(client: Client, torneo: Torneo) -> None:
    cn = categoria_con(torneo, 6)
    generar_fixture(cn, semilla=1)
    a = list(cn.series.get(nombre="A").equipos.order_by("pk"))
    b = list(cn.series.get(nombre="B").equipos.order_by("pk"))
    nuevas = {f"serie_{e.pk}": "A" for e in a} | {f"serie_{e.pk}": "B" for e in b}
    nuevas[f"serie_{a[0].pk}"], nuevas[f"serie_{b[0].pk}"] = "B", "A"
    respuesta = entrar(client, ORGANIZACION).post(f"/torneo/{cn.pk}/series/", nuevas)
    assert respuesta.status_code == 302
    serie_a = set(cn.series.get(nombre="A").equipos.all())
    assert serie_a == {b[0], *a[1:]}
    for partido in cn.partidos.filter(fase="grupos"):
        assert (partido.local in serie_a) != (partido.visitante in serie_a)


@pytest.mark.django_db
def test_series_de_otro_tamanio_no_se_guardan(client: Client, torneo: Torneo) -> None:
    cn = categoria_con(torneo, 6)
    generar_fixture(cn, semilla=1)
    antes = {s.nombre: set(s.equipos.all()) for s in cn.series.all()}
    todas_a = {f"serie_{e.pk}": "A" for e in cn.equipos.all()}
    respuesta = entrar(client, ORGANIZACION).post(f"/torneo/{cn.pk}/series/", todas_a, follow=True)
    assert "las series son de 3 y 3" in respuesta.content.decode()
    assert {s.nombre: set(s.equipos.all()) for s in cn.series.all()} == antes


@pytest.mark.django_db
def test_con_mas_de_diez_equipos_el_fixture_avisa_p27(client: Client, torneo: Torneo) -> None:
    cn = categoria_con(torneo, 11)
    html = entrar(client, ORGANIZACION).get(f"/torneo/{cn.pk}/fixture/").content.decode()
    assert "P27" in html


@pytest.mark.django_db
def test_inicio_ofrece_generar_los_fixtures_que_faltan(client: Client, torneo: Torneo) -> None:
    cn = categoria_con(torneo, 4)
    org = entrar(client, ORGANIZACION)
    html = org.get("/").content.decode()
    assert "1 categoría sin fixture" in html
    assert f'action="/torneos/{torneo.pk}/fixtures/"' in html
    org.post(f"/torneos/{torneo.pk}/fixtures/")
    assert cn.partidos.count() == 10
    assert "sin fixture" not in org.get("/").content.decode()


@pytest.mark.django_db
def test_la_mesa_no_genera_todos(client: Client, torneo: Torneo) -> None:
    categoria_con(torneo, 4)
    assert entrar(client, MESA).post(f"/torneos/{torneo.pk}/fixtures/").status_code == 403


@pytest.mark.django_db
def test_la_pagina_publica_muestra_el_fixture(client: Client, torneo: Torneo) -> None:
    cn = categoria_con(torneo, 4)
    generar_fixture(cn)
    html = client.get(f"/t/{torneo.pk}/{cn.pk}/partidos/").content.decode()
    assert "Fecha 1" in html
    assert "Equipo 0" in html
    assert "Final de Oro" in html
