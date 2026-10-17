"""T13.41: "Calculando…" también en «Rehacer» (cuando hay partidos nuevos para ubicar) y en
«Reprogramar lo cambiado» de una fecha editada (como T13.40). Datos inventados."""

import re
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.template.loader import render_to_string
from django.test import Client, RequestFactory

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Evento, Partido, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture

CALCULANDO = 'data-calculando="Calculando…"'


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 6
    settings.PROGRAMADOR_TRABAJADORES = 2


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


def _categoria(equipos: int) -> CategoriaNivel:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(equipos):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
    generar_fixture(cn, semilla=3)
    return cn


def botones(html: str, texto: str) -> list[str]:
    return re.findall(rf"<button[^>]*>\s*{re.escape(texto)}", html)


@pytest.mark.django_db
def test_rehacer_con_partidos_nuevos_dice_calculando(org: Client) -> None:
    cn = _categoria(7)
    for partido in cn.partidos.filter(fase="grupos", fecha=1):
        partido.estado = Partido.Estado.JUGADO
        partido.save()
        assert partido.local is not None
        Evento.objects.create(partido=partido, tipo="gol", equipo=partido.local)
    Equipo.objects.create(club=Club.objects.create(nombre="Club 8"), categoria=cn, nombre="Nuevo")
    html = org.get(f"/torneo/{cn.pk}/rehacer/").content.decode()
    assert "para programar" in html
    encontrados = botones(html, "Rehacer")
    assert encontrados and all(CALCULANDO in b for b in encontrados)


@pytest.mark.django_db
def test_rehacer_sin_partidos_nuevos_no_calcula(rf: RequestFactory) -> None:
    cn = _categoria(4)
    pedido = rf.get("/")
    pedido.user = User.objects.create_user("org", password="x")
    html = render_to_string(
        "fixture/rehacer.html",
        {"categoria": cn, "conservados": [], "descartados": [], "nuevos": 0},
        request=pedido,
    )
    assert "No hay partidos nuevos" in html
    assert all(CALCULANDO not in b for b in botones(html, "Rehacer"))


@pytest.mark.django_db
def test_reprogramar_lo_cambiado_dice_calculando(org: Client) -> None:
    cn = _categoria(4)
    html = org.get(f"/torneo/{cn.pk}/fecha/1/?editada=1").content.decode()
    encontrados = botones(html, "Reprogramar lo cambiado")
    assert encontrados and all(CALCULANDO in b for b in encontrados)
