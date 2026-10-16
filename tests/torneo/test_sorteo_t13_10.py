"""T13.10: "Falta sorteo" solo cuando la serie terminó (P28). Datos inventados."""

import re

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Partido, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.tabla import tablas_de


@pytest.fixture
def sub9() -> CategoriaNivel:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
    generar_fixture(cn, semilla=1)
    return cn


def falta(cn: CategoriaNivel) -> bool:
    return any(t.falta_sorteo for t in tablas_de(cn))


@pytest.mark.django_db
def test_antes_de_jugar_no_se_pide_sorteo(client: Client, sub9: CategoriaNivel) -> None:
    assert not falta(sub9)
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    html = client.get(f"/torneo/{sub9.pk}/posiciones/").content.decode()
    assert "Falta sorteo" not in html and "Registrar el sorteo" not in html


@pytest.mark.django_db
def test_con_la_serie_a_medias_tampoco(sub9: CategoriaNivel) -> None:
    # Todos empatan 0 a 0 en la fecha 1: siguen empatados, pero la serie no terminó.
    sub9.partidos.filter(fecha=1).update(estado=Partido.Estado.JUGADO)
    assert not falta(sub9)


@pytest.mark.django_db
def test_con_la_serie_terminada_y_empate_total_si(client: Client, sub9: CategoriaNivel) -> None:
    sub9.partidos.filter(fase=Partido.Fase.GRUPOS).update(estado=Partido.Estado.JUGADO)
    assert falta(sub9)
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    html = client.get(f"/torneo/{sub9.pk}/posiciones/").content.decode()
    assert "Falta sorteo" in html
    assert "Registrar el sorteo" in html and not re.search(r"\bP28\b", html)
