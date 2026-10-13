"""T11.11: Partidos de hoy, por cancha y hora, con el estado y el atraso. Datos inventados."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Partido, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


@pytest.fixture
def de_hoy() -> list[Partido]:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
    generar_fixture(cn, semilla=1)
    c2 = torneo.canchas.get(codigo="C2")
    ahora = timezone.now().replace(second=0, microsecond=0)
    partidos = list(cn.partidos.filter(fase="grupos").order_by("pk")[:3])
    turno = timedelta(minutes=cn.minutos_turno)
    for i, partido in enumerate(partidos):
        partido.cancha, partido.inicio = c2, ahora - timedelta(minutes=20) + i * turno
        partido.estado = Partido.Estado.PROGRAMADO
    # El primero empezó 15 minutos tarde.
    primero = partidos[0]
    primero.estado, primero.tiempo = Partido.Estado.EN_JUEGO, Partido.Tiempo.PRIMER_TIEMPO
    assert primero.inicio is not None
    primero.inicio_real = primero.inicio + timedelta(minutes=15)
    for partido in partidos:
        partido.save()
    return partidos


@pytest.mark.django_db
def test_la_lista_por_cancha_con_estado_y_atraso(org: Client, de_hoy: list[Partido]) -> None:
    html = org.get("/hoy/").content.decode()
    assert "Cancha 2" in html
    for partido in de_hoy:
        assert f"/partidos/{partido.pk}/ficha/" in html
    assert "1T " in html  # el que se está jugando
    assert "15 min tarde" in html  # los que siguen


@pytest.mark.django_db
def test_sin_iniciar_pasada_media_hora(org: Client, de_hoy: list[Partido]) -> None:
    primero = de_hoy[0]
    primero.estado, primero.tiempo, primero.inicio_real = Partido.Estado.PROGRAMADO, "", None
    primero.inicio = timezone.now() - timedelta(minutes=40)
    primero.save()
    assert "Sin iniciar" in org.get("/hoy/").content.decode()


@pytest.mark.django_db
def test_esta_en_la_barra(org: Client, de_hoy: list[Partido]) -> None:
    assert 'href="/hoy/"' in org.get("/").content.decode()
