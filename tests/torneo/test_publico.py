"""TU.6: página pública, sin login y sin datos personales (P53)."""

import ast
import re
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion

RAIZ = Path(__file__).resolve().parents[2]
PLANTILLAS_PUBLICAS = RAIZ / "src" / "torneo" / "templates" / "publico"
VISTA_PUBLICA = RAIZ / "src" / "torneo" / "views" / "publico.py"

# Nada que identifique a un menor: ni nombres de jugadores o profes, ni CI ni fechas de nacimiento.
DATOS_PERSONALES = re.compile(
    r"(jugador|persona|profe|documento|nacimiento|fecha_nac|\bci\b|apellido|telefono)", re.I
)
# Ninguno de estos tiene datos de personas (Persona, Jugador y Profe nunca).
MODELOS_PERMITIDOS = {"Torneo", "CategoriaNivel", "Organizador", "Equipo", "Partido", "Serie"}


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    torneo.publico = True
    torneo.save()
    return torneo


@pytest.mark.django_db
def test_se_abre_sin_login(client: Client, torneo: Torneo) -> None:
    respuesta = client.get(f"/t/{torneo.pk}/")
    primera = torneo.categorias.first()
    assert primera is not None
    assert respuesta["Location"] == f"/t/{torneo.pk}/{primera.pk}/partidos/"
    pagina = client.get(respuesta["Location"])
    assert pagina.status_code == 200
    html = pagina.content.decode()
    assert "JMP CUP 2026" in html
    assert 'aria-label="Principal"' not in html  # sin la navegación de la app
    assert "Todavía no hay partidos" in html


@pytest.mark.django_db
def test_un_torneo_no_publico_da_404(client: Client, torneo: Torneo) -> None:
    torneo.publico = False
    torneo.save()
    categoria = torneo.categorias.first()
    assert categoria is not None
    assert client.get(f"/t/{torneo.pk}/").status_code == 404
    assert client.get(f"/t/{torneo.pk}/{categoria.pk}/partidos/").status_code == 404


@pytest.mark.django_db
def test_la_categoria_tiene_que_ser_del_torneo(client: Client, torneo: Torneo) -> None:
    otro = Torneo.objects.create(
        nombre="Otro", edicion=1, anio=2026, inicio=torneo.inicio, fin=torneo.fin, publico=True
    )
    categoria = torneo.categorias.first()
    assert categoria is not None
    assert client.get(f"/t/{otro.pk}/{categoria.pk}/partidos/").status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("pestana", ["partidos", "posiciones", "equipos"])
def test_las_pestanas_publicas_con_htmx(client: Client, torneo: Torneo, pestana: str) -> None:
    categoria = torneo.categorias.first()
    assert categoria is not None
    html = client.get(
        f"/t/{torneo.pk}/{categoria.pk}/{pestana}/", headers={"HX-Request": "true"}
    ).content.decode()
    assert "<html" not in html
    assert 'id="publico"' in html


@pytest.mark.django_db
def test_la_pestana_ajustes_no_existe_en_publico(client: Client, torneo: Torneo) -> None:
    categoria = torneo.categorias.first()
    assert categoria is not None
    assert client.get(f"/t/{torneo.pk}/{categoria.pk}/ajustes/").status_code == 404


@pytest.mark.parametrize("plantilla", sorted(PLANTILLAS_PUBLICAS.rglob("*.html")), ids=str)
def test_las_plantillas_publicas_no_usan_datos_personales(plantilla: Path) -> None:
    variables = re.findall(r"\{[{%](.*?)[}%]\}", plantilla.read_text(), re.S)
    usados = [v for v in variables if DATOS_PERSONALES.search(v)]
    assert not usados, usados


def test_hay_plantillas_publicas() -> None:
    assert list(PLANTILLAS_PUBLICAS.rglob("*.html"))


def test_la_vista_publica_solo_carga_modelos_sin_datos_personales() -> None:
    arbol = ast.parse(VISTA_PUBLICA.read_text())
    importados = {
        nombre.name
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.ImportFrom) and (nodo.module or "").startswith("torneo.models")
        for nombre in nodo.names
    }
    assert importados, "la vista pública tiene que importar sus modelos explícitamente"
    assert importados <= MODELOS_PERMITIDOS, importados - MODELOS_PERMITIDOS


def entrar(client: Client, grupo: str) -> Client:
    usuario = User.objects.create_user(grupo[:4], password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


@pytest.mark.django_db
def test_la_organizacion_publica_y_despublica(client: Client, torneo: Torneo) -> None:
    org = entrar(client, ORGANIZACION)
    assert org.post(f"/torneos/{torneo.pk}/publico/").status_code == 302
    torneo.refresh_from_db()
    assert not torneo.publico
    org.post(f"/torneos/{torneo.pk}/publico/")
    torneo.refresh_from_db()
    assert torneo.publico


@pytest.mark.django_db
def test_la_mesa_no_publica(client: Client, torneo: Torneo) -> None:
    assert entrar(client, MESA).post(f"/torneos/{torneo.pk}/publico/").status_code == 403


@pytest.mark.django_db
def test_inicio_enlaza_la_pagina_publica_solo_si_esta_publicada(
    client: Client, torneo: Torneo
) -> None:
    mesa = entrar(client, MESA)
    assert f'href="/t/{torneo.pk}/"' in mesa.get("/").content.decode()
    torneo.publico = False
    torneo.save()
    assert f'href="/t/{torneo.pk}/"' not in mesa.get("/").content.decode()
