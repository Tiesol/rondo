"""T13.9: pendientes de Inicio y avisos del fixture. Datos inventados."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.pendientes import pendientes


@pytest.fixture
def torneo() -> Torneo:
    return cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))


def con_fixture(torneo: Torneo, cuantos: int) -> CategoriaNivel:
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(cuantos):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
    generar_fixture(cn, semilla=1)
    return cn


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


@pytest.mark.django_db
def test_ya_no_esta_el_pendiente_de_las_reglas(torneo: Torneo) -> None:
    titulos = [p["titulo"] for p in pendientes(torneo, puede_configurar=True)]
    assert not any("reglas" in t for t in titulos)


@pytest.mark.django_db
def test_los_partidos_sin_dia_ni_hora_son_un_pendiente(torneo: Torneo) -> None:
    cn = con_fixture(torneo, 4)
    total = cn.partidos.count()
    lista = pendientes(torneo, puede_configurar=True)
    (sin_programar,) = [p for p in lista if "sin día ni hora" in p["titulo"]]
    assert sin_programar["titulo"] == f"{total} partidos sin día ni hora"
    assert sin_programar["url"] == f"/torneos/{torneo.pk}/programar/"
    # La mesa no programa: no se lo muestra.
    assert not any(
        "sin día ni hora" in p["titulo"] for p in pendientes(torneo, puede_configurar=False)
    )


@pytest.mark.django_db
def test_la_pestana_fixture_avisa_y_lleva_a_programar(org: Client, torneo: Torneo) -> None:
    cn = con_fixture(torneo, 4)
    html = org.get(f"/torneo/{cn.pk}/fixture/").content.decode()
    assert "sin día ni hora" in html
    assert f"/torneos/{torneo.pk}/programar/" in html


@pytest.mark.django_db
def test_las_series_cruzadas_se_explican(org: Client, torneo: Torneo) -> None:
    cn = con_fixture(torneo, 6)
    html = org.get(f"/torneo/{cn.pk}/fixture/").content.decode()
    assert "Cada equipo de A juega con todos los de B" in html
    assert "1.º A vs 2.º A" in html and "1.º B vs 2.º B" in html


@pytest.mark.django_db
def test_con_series_normales_no_hay_texto_de_cruzadas(org: Client, torneo: Torneo) -> None:
    cn = con_fixture(torneo, 8)
    html = org.get(f"/torneo/{cn.pk}/fixture/").content.decode()
    assert "Cada equipo de A juega con todos los de B" not in html
