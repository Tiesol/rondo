"""T7.11: borrador del calendario y aviso de fixture desactualizado. Datos inventados."""

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
from torneo.servicios.fixture import generar_fixture, motivo_desactualizado
from torneo.servicios.programador import programar_torneo


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10
    settings.PROGRAMADOR_TRABAJADORES = 4


@pytest.fixture
def torneo() -> Torneo:
    return cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))


def con_equipos(torneo: Torneo, cantidad: int) -> CategoriaNivel:
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(cantidad):
        club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
        Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}")
    return cn


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


def dia_con_partidos() -> str:
    primero = Partido.objects.filter(inicio__isnull=False).order_by("inicio").first()
    assert primero is not None and primero.inicio is not None
    return timezone.localtime(primero.inicio).date().isoformat()


# ---------- Borrador ----------


@pytest.mark.django_db
def test_con_la_pagina_publica_apagada_el_calendario_y_el_png_dicen_borrador(
    org: Client, torneo: Torneo
) -> None:
    generar_fixture(con_equipos(torneo, 4), semilla=1)
    programar_torneo(torneo)
    dia = dia_con_partidos()
    assert not torneo.publico
    assert "Borrador" in org.get(f"/calendario/{dia}/").content.decode()
    assert "BORRADOR" in org.get(f"/calendario/{dia}/png/").content.decode()

    torneo.publico = True
    torneo.save()
    assert "Borrador" not in org.get(f"/calendario/{dia}/").content.decode()
    assert "BORRADOR" not in org.get(f"/calendario/{dia}/png/").content.decode()


# ---------- Fixture desactualizado ----------


@pytest.mark.django_db
def test_agregar_un_equipo_despues_del_fixture_lo_deja_desactualizado(
    org: Client, torneo: Torneo
) -> None:
    cn = con_equipos(torneo, 4)
    generar_fixture(cn, semilla=1)
    assert motivo_desactualizado(cn) == ""
    Equipo.objects.create(club=Club.objects.create(nombre="Tarde"), categoria=cn, nombre="Tarde")
    assert motivo_desactualizado(cn)
    fixture = org.get(f"/torneo/{cn.pk}/fixture/").content.decode()
    assert "El fixture de esta categoría está desactualizado" in fixture
    assert f"/torneo/{cn.pk}/fixture/generar/" in fixture
    assert "desactualizado" in org.get("/").content.decode()


@pytest.mark.django_db
def test_sacar_un_equipo_tambien(torneo: Torneo) -> None:
    cn = con_equipos(torneo, 5)
    generar_fixture(cn, semilla=1)
    otra = torneo.categorias.get(categoria="Sub 9", nivel="inicial")
    Equipo.objects.filter(pk=cn.equipos.order_by("pk").last().pk).update(categoria=otra)  # type: ignore[union-attr]
    assert motivo_desactualizado(cn)


@pytest.mark.django_db
def test_rehacer_quita_el_aviso_y_la_programacion_vieja(org: Client, torneo: Torneo) -> None:
    cn = con_equipos(torneo, 4)
    generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    assert cn.partidos.filter(inicio__isnull=False).exists()
    Equipo.objects.create(club=Club.objects.create(nombre="Tarde"), categoria=cn, nombre="Tarde")
    org.post(f"/torneo/{cn.pk}/fixture/generar/")
    assert motivo_desactualizado(cn) == ""
    assert cn.partidos.count() == 12  # el formato de 5
    assert not cn.partidos.filter(inicio__isnull=False).exists()


@pytest.mark.django_db
def test_cambiar_la_copa_de_bronce_con_10_equipos_lo_deja_desactualizado(torneo: Torneo) -> None:
    cn = con_equipos(torneo, 10)
    generar_fixture(cn, semilla=1)
    assert motivo_desactualizado(cn) == ""
    torneo.reglas = torneo.reglas | {"copa_de_bronce": True}
    torneo.save()
    assert "Bronce" in motivo_desactualizado(cn)
