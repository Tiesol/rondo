"""T13.39: en "Un equipo no puede jugar", elegir el club trae sus equipos sin tocar un botón
(HTMX), y las casillas van en la misma línea que su texto. Datos inventados."""

import re

import pytest
from django import forms
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.template.loader import render_to_string
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    for nombre in ("Norte FC", "Sur FC"):
        club = Club.objects.create(nombre=nombre)
        for categoria in ("Sub 9", "Sub 10"):
            Equipo.objects.create(
                club=club,
                categoria=torneo.categorias.get(categoria=categoria, nivel="inicial"),
                nombre=nombre.split()[0],
            )
    return torneo


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


def _selector(html: str) -> str:
    """El formulario del club, desde <form hasta </form>."""
    inicio = html.index('<form method="get"')
    return html[inicio : html.index("</form>", inicio)]


@pytest.mark.django_db
def test_cambiar_el_club_pide_sus_equipos_con_htmx(org: Client, torneo: Torneo) -> None:
    selector = _selector(org.get(f"/torneos/{torneo.pk}/acf/").content.decode())
    assert f'hx-get="/torneos/{torneo.pk}/acf/"' in selector
    assert 'hx-trigger="change"' in selector
    assert 'hx-target="#bloqueo-acf"' in selector


@pytest.mark.django_db
def test_el_boton_ver_sus_equipos_queda_solo_sin_javascript(org: Client, torneo: Torneo) -> None:
    selector = _selector(org.get(f"/torneos/{torneo.pk}/acf/").content.decode())
    assert re.search(r"<noscript>\s*<button[^>]*>Ver sus equipos</button>\s*</noscript>", selector)


@pytest.mark.django_db
def test_con_htmx_vuelven_solo_los_equipos_del_club(org: Client, torneo: Torneo) -> None:
    norte = Club.objects.get(nombre="Norte FC")
    html = org.get(
        f"/torneos/{torneo.pk}/acf/?club={norte.pk}", headers={"HX-Request": "true"}
    ).content.decode()
    assert html.lstrip().startswith('<div id="bloqueo-acf"')
    assert html.count('name="equipos"') == 2
    assert "Bloqueos cargados" not in html and "<html" not in html


@pytest.mark.django_db
def test_con_htmx_y_sin_club_queda_el_lugar_vacio(org: Client, torneo: Torneo) -> None:
    html = org.get(f"/torneos/{torneo.pk}/acf/?club=", headers={"HX-Request": "true"})
    texto = html.content.decode()
    assert '<div id="bloqueo-acf"' in texto and 'name="equipos"' not in texto


@pytest.mark.django_db
def test_sin_htmx_la_pagina_entera_tiene_el_lugar_de_los_equipos(
    org: Client, torneo: Torneo
) -> None:
    norte = Club.objects.get(nombre="Norte FC")
    html = org.get(f"/torneos/{torneo.pk}/acf/?club={norte.pk}").content.decode()
    assert '<div id="bloqueo-acf"' in html and "Bloqueos cargados" in html
    assert html.count('name="equipos"') == 2


CASILLA_EN_SU_LINEA = re.compile(
    r'<label class="opcion"[^>]*>\s*<input type="checkbox" name="equipos"[^>]*>\s*\S'
)


@pytest.mark.django_db
def test_cada_casilla_va_en_la_misma_linea_que_su_texto(org: Client, torneo: Torneo) -> None:
    norte = Club.objects.get(nombre="Norte FC")
    html = org.get(f"/torneos/{torneo.pk}/acf/?club={norte.pk}").content.decode()
    assert len(CASILLA_EN_SU_LINEA.findall(html)) == 2


class _ConCasillas(forms.Form):
    lados = forms.MultipleChoiceField(
        label="Lados",
        choices=[("a", "Local"), ("b", "Visitante")],
        widget=forms.CheckboxSelectMultiple,
        help_text="Uno o los dos.",
    )


def test_el_campo_de_casillas_las_pinta_como_opciones() -> None:
    # Lo usa también «¿Quién no puede?» en Reprogramar un partido.
    html = render_to_string("parciales/campo.html", {"campo": _ConCasillas()["lados"]})
    assert re.search(r"<fieldset[^>]*>\s*<legend[^>]*>Lados</legend>", html)
    assert len(re.findall(r'<label class="opcion"[^>]*>\s*<input type="checkbox"', html)) == 2
    assert "Local" in html and "Visitante" in html and "Uno o los dos." in html
