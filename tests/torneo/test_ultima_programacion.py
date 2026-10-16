"""T13.36: el resultado de la última programación dice cuándo fue, se marca desactualizado si
después cambió el fixture o se movieron partidos, y se puede ocultar."""

from datetime import datetime, timedelta
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
from torneo.views.programar import cuando


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10
    settings.PROGRAMADOR_TRABAJADORES = 4


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
        Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}")
    generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    return torneo


def entrar(client: Client, grupo: str = ORGANIZACION) -> Client:
    usuario = User.objects.create_user(grupo[:4], password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


def pantalla(client: Client, torneo: Torneo) -> str:
    return client.get(f"/torneos/{torneo.pk}/programar/").content.decode()


def test_cuando_en_palabras() -> None:
    ahora = timezone.make_aware(datetime(2026, 10, 24, 19, 20))
    assert cuando(ahora, ahora=ahora) == "hoy 19:20"
    assert cuando(ahora - timedelta(days=1), ahora=ahora) == "ayer 19:20"
    assert cuando(ahora - timedelta(days=3), ahora=ahora) == "mié 21/10 19:20"


@pytest.mark.django_db
def test_dice_cuando_fue_y_no_esta_desactualizada(client: Client, torneo: Torneo) -> None:
    html = pantalla(entrar(client), torneo)
    corrida = Corrida.objects.filter(torneo=torneo).first()
    assert corrida is not None
    assert f"Última programación: {cuando(corrida.inicio)}" in html
    assert "Desactualizada" not in html


@pytest.mark.django_db
def test_mover_un_partido_la_deja_desactualizada(client: Client, torneo: Torneo) -> None:
    partido = Partido.objects.filter(categoria__torneo=torneo, inicio__isnull=False).first()
    assert partido is not None and partido.inicio is not None
    Partido.objects.filter(pk=partido.pk).update(inicio=partido.inicio + timedelta(minutes=5))
    html = pantalla(entrar(client), torneo)
    assert "Desactualizada" in html
    assert "Después se cambió el fixture o se movieron partidos" in html
    assert '<details class="desplegable"' in html  # el resultado viejo, plegado


@pytest.mark.django_db
def test_cambiar_el_fixture_la_deja_desactualizada(client: Client, torneo: Torneo) -> None:
    Partido.objects.filter(categoria__torneo=torneo).first().delete()  # type: ignore[union-attr]
    assert "Desactualizada" in pantalla(entrar(client), torneo)


@pytest.mark.django_db
def test_ocultar_la_saca_hasta_la_proxima(client: Client, torneo: Torneo) -> None:
    entrar(client)
    respuesta = client.post(f"/torneos/{torneo.pk}/programar/ocultar/")
    assert respuesta.status_code == 302
    assert "Última programación" not in pantalla(client, torneo)
    programar_torneo(torneo)
    assert "Última programación" in pantalla(client, torneo)


@pytest.mark.django_db
def test_la_mesa_no_puede_ocultarla(client: Client, torneo: Torneo) -> None:
    respuesta = entrar(client, MESA).post(f"/torneos/{torneo.pk}/programar/ocultar/")
    assert respuesta.status_code == 403
    corrida = Corrida.objects.filter(torneo=torneo).first()
    assert corrida is not None and not corrida.resultado.get("oculta")
