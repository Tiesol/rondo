"""T10.10: al reprogramar por un pedido, dar W.O. y saber cuántas veces reprogramó el equipo."""

from datetime import timedelta
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Bloqueo, CategoriaNivel, Club, Corrida, Equipo, Partido
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.partido import resultado_de
from torneo.servicios.programador import programar_torneo


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10
    settings.PROGRAMADOR_TRABAJADORES = 4


@pytest.fixture
def victima() -> Partido:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(6):
        club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
        Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}")
    generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    partido = Partido.objects.filter(fase="grupos", inicio__isnull=False).order_by("inicio").first()
    assert partido is not None and partido.inicio is not None
    return partido


def pedido(partido: Partido) -> Bloqueo:
    assert partido.inicio is not None and partido.local is not None
    bloqueo = Bloqueo.objects.create(
        torneo=partido.categoria.torneo,
        inicio=partido.inicio - timedelta(minutes=10),
        fin=partido.inicio + timedelta(hours=1),
    )
    bloqueo.equipos.add(partido.local)
    return bloqueo


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


@pytest.mark.django_db
def test_desde_las_propuestas_se_da_wo_al_equipo_que_pidio(org: Client, victima: Partido) -> None:
    org.post(f"/bloqueos/{pedido(victima).pk}/propuestas/")
    corrida = Corrida.objects.get(tipo=Corrida.Tipo.REPROGRAMAR)
    html = org.get(f"/corridas/{corrida.pk}/propuestas/").content.decode()
    assert "Dar W.O." in html
    org.post(f"/corridas/{corrida.pk}/wo/", {"partido": victima.pk, "equipo": victima.local_id})
    victima.refresh_from_db()
    assert victima.estado == Partido.Estado.JUGADO and victima.no_se_presento == "local"
    assert resultado_de(victima).marcador == (0, 3)


@pytest.mark.django_db
def test_avisa_cuantas_veces_reprogramo_el_equipo(org: Client, victima: Partido) -> None:
    org.post(f"/bloqueos/{pedido(victima).pk}/propuestas/")
    primera = Corrida.objects.get(tipo=Corrida.Tipo.REPROGRAMAR)
    assert "ya reprogramó" not in org.get(f"/corridas/{primera.pk}/propuestas/").content.decode()
    org.post(f"/corridas/{primera.pk}/aplicar/0/")
    victima.refresh_from_db()
    org.post(f"/bloqueos/{pedido(victima).pk}/propuestas/")
    segunda = Corrida.objects.filter(tipo=Corrida.Tipo.REPROGRAMAR).latest("pk")
    html = org.get(f"/corridas/{segunda.pk}/propuestas/").content.decode()
    assert f"{victima.local.nombre} ya reprogramó 1 vez" in html  # type: ignore[union-attr]
