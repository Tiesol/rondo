"""T13.7 (P86c): con 2 equipos la categoría no se abre (convocatoria 2026). Datos inventados."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from dominio.formatos import CategoriaNoSeAbre
from torneo.models import CategoriaNivel, Club, Equipo, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import FixtureNoSePuede, formatos, generar_fixture
from torneo.servicios.pendientes import pendientes


@pytest.fixture
def torneo() -> Torneo:
    return cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))


def con_equipos(torneo: Torneo, cuantos: int) -> CategoriaNivel:
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(cuantos):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
    return cn


def test_el_minimo_sale_de_formatos_json() -> None:
    with pytest.raises(CategoriaNoSeAbre, match="no se abre"):
        formatos().para(2)
    assert formatos().para(3).equipos == 3


@pytest.mark.django_db
def test_con_dos_equipos_no_se_arma_el_fixture(torneo: Torneo) -> None:
    cn = con_equipos(torneo, 2)
    with pytest.raises(FixtureNoSePuede, match="no se abre"):
        generar_fixture(cn, semilla=1)
    assert not cn.partidos.exists()


@pytest.mark.django_db
def test_inicio_dice_que_no_se_abre_y_no_que_falta_el_fixture(torneo: Torneo) -> None:
    con_equipos(torneo, 2)
    titulos = [p["titulo"] for p in pendientes(torneo, puede_configurar=True)]
    assert "1 categoría no se abre: tiene 2 equipos" in titulos
    assert not any("sin fixture" in t for t in titulos)


@pytest.mark.django_db
def test_la_pestana_fixture_lo_dice(client: Client, torneo: Torneo) -> None:
    cn = con_equipos(torneo, 2)
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    html = client.get(f"/torneo/{cn.pk}/fixture/").content.decode()
    assert "Con 2 equipos la categoría no se abre" in html
