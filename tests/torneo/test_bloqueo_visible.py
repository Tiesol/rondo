"""T13.16: un partido que choca con un bloqueo se ve en Inicio, el calendario, el fixture y la
ficha; desde el bloqueo se mueve a mano, se intercambia o se ven las propuestas. Datos
inventados."""

from datetime import timedelta
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import Bloqueo, CategoriaNivel, Club, Equipo, Partido, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.bloqueos import chocan_con_bloqueos
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.pendientes import pendientes
from torneo.servicios.programador import programar_torneo


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
    generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    return torneo


@pytest.fixture
def choca(torneo: Torneo) -> Partido:
    partido = Partido.objects.filter(inicio__isnull=False).order_by("inicio").first()
    assert partido is not None and partido.inicio is not None
    bloqueo = Bloqueo.objects.create(
        torneo=torneo,
        inicio=partido.inicio - timedelta(minutes=30),
        fin=partido.inicio + timedelta(minutes=30),
        motivo="Partido de la ACF",
    )
    assert partido.local is not None
    bloqueo.equipos.set([partido.local])
    return partido


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


@pytest.mark.django_db
def test_el_servicio_dice_que_partidos_chocan(torneo: Torneo, choca: Partido) -> None:
    assert chocan_con_bloqueos(torneo) == {choca.pk: "Partido de la ACF"}


@pytest.mark.django_db
def test_inicio_tiene_el_pendiente(torneo: Torneo, choca: Partido) -> None:
    (fila,) = [p for p in pendientes(torneo, puede_configurar=True) if "bloqueo" in p["titulo"]]
    assert fila["titulo"] == "1 partido choca con un bloqueo"
    assert fila["url"] == f"/torneos/{torneo.pk}/acf/"


@pytest.mark.django_db
def test_calendario_fixture_y_ficha_lo_marcan(org: Client, torneo: Torneo, choca: Partido) -> None:
    dia = timezone.localtime(choca.inicio).date().isoformat()
    assert "Choca con un bloqueo" in org.get(f"/calendario/{dia}/").content.decode()
    assert (
        "Choca con un bloqueo" in org.get(f"/torneo/{choca.categoria_id}/fixture/").content.decode()
    )
    ficha = org.get(f"/partidos/{choca.pk}/ficha/").content.decode()
    assert "Choca con un bloqueo" in ficha and f"/partidos/{choca.pk}/reprogramar/" in ficha


@pytest.mark.django_db
def test_el_bloqueo_ofrece_mover_e_intercambiar(
    org: Client, torneo: Torneo, choca: Partido
) -> None:
    html = org.get(f"/torneos/{torneo.pk}/acf/").content.decode()
    assert f"/partidos/{choca.pk}/mover/" in html
    assert f"/partidos/{choca.pk}/intercambiar/" in html
    assert "Ver propuestas" in html


@pytest.mark.django_db
def test_sin_choques_no_hay_marcas(org: Client, torneo: Torneo) -> None:
    assert chocan_con_bloqueos(torneo) == {}
    assert not any("bloqueo" in p["titulo"] for p in pendientes(torneo, puede_configurar=True))
