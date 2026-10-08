"""T4.6: programar desde la pantalla y ver el calendario por día y cancha."""

from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Corrida, Equipo, Partido, Torneo
from torneo.permisos import MESA, ORGANIZACION
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
    torneo.publico = True
    torneo.save()
    for categoria, nivel in (("Sub 9", "avanzado"), ("Sub 6", "unico")):
        cn: CategoriaNivel = torneo.categorias.get(categoria=categoria, nivel=nivel)
        for i in range(4):
            club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
            Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}")
        generar_fixture(cn, semilla=1)
    return torneo


def entrar(client: Client, grupo: str) -> Client:
    usuario = User.objects.create_user(grupo[:4], password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


@pytest.mark.django_db
def test_la_organizacion_programa_y_ve_el_resultado(client: Client, torneo: Torneo) -> None:
    org = entrar(client, ORGANIZACION)
    respuesta = org.post(f"/torneos/{torneo.pk}/programar/")
    assert respuesta.status_code == 302
    html = org.get(f"/torneos/{torneo.pk}/programar/").content.decode()
    assert "20 de 20 partidos programados" in html
    assert "sin choques" in html
    assert 'href="/calendario/' in html


@pytest.mark.django_db
def test_con_htmx_vuelve_solo_el_resultado(client: Client, torneo: Torneo) -> None:
    html = (
        entrar(client, ORGANIZACION)
        .post(f"/torneos/{torneo.pk}/programar/", headers={"HX-Request": "true"})
        .content.decode()
    )
    assert "<html" not in html
    assert 'id="resultado-programacion"' in html
    assert Corrida.objects.filter(estado="terminada").exists()


@pytest.mark.django_db
def test_si_ya_hay_una_corriendo_lo_dice(client: Client, torneo: Torneo) -> None:
    Corrida.objects.create(torneo=torneo, estado=Corrida.Estado.CORRIENDO)
    respuesta = entrar(client, ORGANIZACION).post(f"/torneos/{torneo.pk}/programar/", follow=True)
    assert "Ya hay una programación corriendo" in respuesta.content.decode()


@pytest.mark.django_db
def test_la_mesa_no_programa_pero_ve_el_calendario(client: Client, torneo: Torneo) -> None:
    programar_torneo(torneo)
    mesa = entrar(client, MESA)
    assert mesa.post(f"/torneos/{torneo.pk}/programar/").status_code == 403
    respuesta = mesa.get("/calendario/", follow=True)
    assert respuesta.status_code == 200
    assert "Cancha 1" in respuesta.content.decode()


@pytest.mark.django_db
def test_el_calendario_de_un_dia_por_cancha_y_en_orden(client: Client, torneo: Torneo) -> None:
    programar_torneo(torneo)
    primero = (
        Partido.objects.filter(categoria__torneo=torneo, inicio__isnull=False)
        .order_by("inicio")
        .first()
    )
    assert primero is not None and primero.inicio is not None
    dia = timezone.localtime(primero.inicio).date()
    html = entrar(client, MESA).get(f"/calendario/{dia.isoformat()}/").content.decode()
    assert timezone.localtime(primero.inicio).strftime("%H:%M") in html
    horas = [
        timezone.localtime(p.inicio).strftime("%H:%M")
        for p in Partido.objects.filter(
            categoria__torneo=torneo, cancha=primero.cancha, inicio__date=dia
        ).order_by("inicio")
        if p.inicio
    ]
    posiciones = [html.index(h) for h in horas]
    assert posiciones == sorted(posiciones)
    assert 'aria-current="page"' in html  # el día elegido y el menú


@pytest.mark.django_db
def test_un_dia_sin_partidos(client: Client, torneo: Torneo) -> None:
    html = entrar(client, MESA).get("/calendario/2026-10-23/").content.decode()
    assert "No hay partidos programados este día" in html


@pytest.mark.django_db
def test_la_pagina_publica_muestra_dia_y_hora(client: Client, torneo: Torneo) -> None:
    programar_torneo(torneo)
    sub9 = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    partido = Partido.objects.filter(categoria=sub9, inicio__isnull=False).first()
    assert partido is not None and partido.inicio is not None
    html = client.get(f"/t/{torneo.pk}/{sub9.pk}/partidos/").content.decode()
    assert timezone.localtime(partido.inicio).strftime("%H:%M") in html
