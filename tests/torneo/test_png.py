"""T5.6: el PNG del día por cancha, sin datos personales (criterio 6). Datos inventados."""

import ast
import re
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Partido, Torneo
from torneo.permisos import MESA
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo

RAIZ = Path(__file__).resolve().parents[2]
PLANTILLAS_PNG = [
    RAIZ / "src" / "torneo" / "templates" / "calendario" / "png.html",
    RAIZ / "src" / "torneo" / "templates" / "calendario" / "_pieza.html",
]
VISTA = RAIZ / "src" / "torneo" / "views" / "png.py"
DATOS_PERSONALES = re.compile(
    r"(jugador|persona|profe|documento|nacimiento|fecha_nac|\bci\b|apellido|telefono)", re.I
)


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10
    settings.PROGRAMADOR_TRABAJADORES = 4


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(6):
        club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
        Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}", color_1="#c8102e")
    generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    return torneo


def mesa(client: Client) -> Client:
    usuario = User.objects.create_user("mesa", password="x")
    usuario.groups.add(Group.objects.get(name=MESA))
    client.force_login(usuario)
    return client


def un_dia_con_partidos() -> str:
    partido = Partido.objects.filter(inicio__isnull=False).order_by("inicio").first()
    assert partido is not None and partido.inicio is not None
    return timezone.localtime(partido.inicio).date().isoformat()


@pytest.mark.django_db
def test_una_pieza_por_cancha_con_sus_partidos(client: Client, torneo: Torneo) -> None:
    dia = un_dia_con_partidos()
    html = mesa(client).get(f"/calendario/{dia}/png/").content.decode()
    assert "FIXTURE" in html
    assert 'class="pieza"' in html
    assert "data-exportar" in html
    assert "Compartir todas" in html
    del_dia = [
        p
        for p in Partido.objects.filter(inicio__isnull=False).select_related("local")
        if p.inicio and timezone.localtime(p.inicio).date().isoformat() == dia
    ]
    for partido in del_dia:
        assert timezone.localtime(partido.inicio).strftime("%H:%M") in html
    assert "5.ª EDICIÓN" in html.upper() or "5.ª edición" in html


@pytest.mark.django_db
def test_mas_de_cinco_partidos_en_una_cancha_van_en_varias_imagenes(
    client: Client, torneo: Torneo
) -> None:
    dia = un_dia_con_partidos()
    primero = Partido.objects.filter(inicio__isnull=False).order_by("inicio").first()
    assert primero is not None and primero.inicio is not None
    # Siete partidos en la misma cancha ese día (el PNG no verifica: solo muestra).
    for i, partido in enumerate(Partido.objects.filter(fase="grupos")[:7]):
        Partido.objects.filter(pk=partido.pk).update(
            cancha=primero.cancha, inicio=primero.inicio + timedelta(minutes=50 * i)
        )
    html = mesa(client).get(f"/calendario/{dia}/png/").content.decode()
    assert "1/2" in html and "2/2" in html


@pytest.mark.django_db
def test_el_calendario_ofrece_compartir_el_dia(client: Client, torneo: Torneo) -> None:
    dia = un_dia_con_partidos()
    html = mesa(client).get(f"/calendario/{dia}/").content.decode()
    assert f'href="/calendario/{dia}/png/"' in html


@pytest.mark.parametrize("plantilla", PLANTILLAS_PNG, ids=lambda p: p.name)
def test_el_png_no_usa_datos_personales(plantilla: Path) -> None:
    variables = re.findall(r"\{[{%](.*?)[}%]\}", plantilla.read_text(), re.S)
    assert not [v for v in variables if DATOS_PERSONALES.search(v)]


def test_la_vista_del_png_no_carga_modelos_de_personas() -> None:
    arbol = ast.parse(VISTA.read_text())
    importados = {
        nombre.name
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.ImportFrom) and (nodo.module or "").startswith("torneo.models")
        for nombre in nodo.names
    }
    assert importados
    assert importados <= {"Torneo", "Partido", "Cancha", "Equipo", "Organizador"}


@pytest.mark.django_db
def test_la_pagina_de_prueba_del_png_ya_no_esta(client: Client) -> None:
    client.force_login(User.objects.create_superuser("seba", password="x"))
    assert client.get("/diagnostico/png/").status_code == 404
