"""TU.1: base visual. Tokens de DISENO.md, plantilla base, navegación y parciales."""

import re
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.test import Client

from torneo.models import Organizador

RAIZ = Path(__file__).resolve().parents[2]
PLANTILLAS = RAIZ / "src" / "torneo" / "templates"
CSS = RAIZ / "frontend" / "tailwind.css"
FUENTES = RAIZ / "src" / "torneo" / "static" / "fuentes"

FUERA_DE_LOS_TOKENS: set[Path] = set()

PALETA_DE_TAILWIND = re.compile(
    r"\b(?:bg|text|border|outline|ring|fill|stroke|from|via|to|decoration|divide|accent|caret"
    r"|shadow)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald"
    r"|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|white|black)\b"
)
COLOR_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def plantillas_con_tokens() -> list[Path]:
    return [p for p in PLANTILLAS.rglob("*.html") if p not in FUERA_DE_LOS_TOKENS]


@pytest.mark.parametrize("plantilla", plantillas_con_tokens(), ids=lambda p: p.name)
def test_ningun_color_esta_escrito_a_mano_en_las_plantillas(plantilla: Path) -> None:
    texto = plantilla.read_text()
    assert not PALETA_DE_TAILWIND.findall(texto), "usar los colores de los tokens"
    assert not COLOR_HEX.findall(texto), "usar los colores de los tokens"


def test_los_tokens_de_disenio_estan_en_claro_y_en_oscuro() -> None:
    css = CSS.read_text()
    for token in ("#0d2440", "#f2cf3a"):
        assert token in css
    assert "prefers-color-scheme: dark" in css
    assert re.search(r":focus-visible\s*\{[^}]*var\(--color-oro\)", css), "foco visible en dorado"


def test_las_fuentes_se_sirven_desde_la_app_y_no_desde_google() -> None:
    css = CSS.read_text()
    for archivo in re.findall(r'url\("\.\./fuentes/([^"]+)"\)', css):
        assert (FUENTES / archivo).is_file(), archivo
    assert "Bebas Neue" in css
    assert "Figtree" in css
    todo = css + "".join(p.read_text() for p in PLANTILLAS.rglob("*.html"))
    assert "fonts.googleapis" not in todo
    assert "fonts.gstatic" not in todo


@pytest.mark.parametrize(
    ("nombre", "sigla"),
    [
        ("JMP Soccer School", "JMP"),
        ("Academia Tahuichi Aguilera", "ATA"),
        ("Club Bolívar", "CB"),
        ("Rondo", "R"),
    ],
)
def test_la_sigla_del_organizador_sale_de_su_nombre(nombre: str, sigla: str) -> None:
    assert Organizador(nombre=nombre).sigla == sigla


@pytest.fixture
def con_sesion(client: Client) -> Client:
    client.force_login(User.objects.create_user("org", password="x"))
    return client


@pytest.mark.django_db
def test_el_inicio_tiene_barra_superior_y_navegacion_principal(con_sesion: Client) -> None:
    html = con_sesion.get("/").content.decode()
    assert 'class="barra' in html
    assert 'aria-label="Principal"' in html
    assert re.search(r'<a [^>]*href="/"[^>]*aria-current="page"', html)
    for seccion in ("Inicio", "Torneo", "Calendario", "Más"):
        assert seccion in html
    assert "JMP" in html  # la sigla del organizador


@pytest.mark.django_db
def test_las_cuatro_secciones_del_menu_ya_son_enlaces(con_sesion: Client) -> None:
    html = con_sesion.get("/").content.decode()
    for destino in ('href="/"', 'href="/torneo/"', 'href="/calendario/"', 'href="/mas/"'):
        assert destino in html
    assert 'aria-disabled="true"' not in html


def test_lo_que_todavia_no_existe_se_ve_desactivado_en_el_menu() -> None:
    html = render_to_string(
        "parciales/nav_item.html", {"destino": "no-existe", "texto": "Pronto", "icono": "mas"}
    )
    assert re.search(r'aria-disabled="true"[^>]*>.*?Pronto', html, re.DOTALL)


@pytest.mark.django_db
def test_el_admin_ya_no_esta_en_el_menu(client: Client) -> None:
    client.force_login(User.objects.create_user("staff", password="x", is_staff=True))
    assert "/admin/" not in client.get("/").content.decode()


@pytest.mark.django_db
def test_el_login_no_muestra_la_navegacion(client: Client) -> None:
    html = client.get("/cuentas/login/").content.decode()
    assert 'aria-label="Principal"' not in html
    assert "Iniciar sesión" in html


URL_COMPONENTES = "/diagnostico/componentes/"


@pytest.mark.django_db
def test_la_pagina_de_componentes_es_solo_para_staff(con_sesion: Client) -> None:
    assert con_sesion.get(URL_COMPONENTES).status_code == 403


@pytest.mark.django_db
def test_la_pagina_de_componentes_muestra_todos_los_parciales(client: Client) -> None:
    client.force_login(User.objects.create_user("staff", password="x", is_staff=True))
    respuesta = client.get(URL_COMPONENTES)
    assert respuesta.status_code == 200
    usadas = {t.name for t in respuesta.templates}
    parciales = {f"parciales/{p.name}" for p in (PLANTILLAS / "parciales").glob("*.html")}
    assert parciales, "faltan los parciales"
    assert parciales <= usadas, parciales - usadas
