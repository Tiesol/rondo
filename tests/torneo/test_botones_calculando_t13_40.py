"""T13.40: los botones que calculan se bloquean y dicen "Calculando…" mientras esperan.

El POST de propuestas se mandó 4 veces: se tocaba de nuevo, y el celular reenviaba al volver de
minimizar la app. Las plantillas marcan esos botones con `data-calculando`; `ui.js` los
desactiva y no deja salir un segundo envío del mismo formulario. Datos inventados.
"""

import re
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Bloqueo, CategoriaNivel, Club, Equipo, Partido, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo
from torneo.servicios.reprogramar import calcular_propuestas

CALCULANDO = 'data-calculando="Calculando…"'


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
    generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    return torneo


@pytest.fixture
def partido(torneo: Torneo) -> Partido:
    p = Partido.objects.filter(inicio__isnull=False).order_by("inicio").first()
    assert p is not None
    return p


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


@pytest.fixture
def bloqueo(partido: Partido) -> Bloqueo:
    assert partido.inicio is not None and partido.local is not None
    bloqueo = Bloqueo.objects.create(
        torneo=partido.categoria.torneo,
        inicio=partido.inicio,
        fin=partido.inicio + timedelta(hours=1),
        motivo="Partido de la ACF",
    )
    bloqueo.equipos.set([partido.local])
    return bloqueo


def botones(html: str, texto: str) -> list[str]:
    """La etiqueta de apertura de cada <button> cuyo texto empieza con `texto`."""
    return re.findall(rf"<button[^>]*>\s*{re.escape(texto)}", html)


@pytest.mark.django_db
def test_ver_propuestas_al_reprogramar_un_partido(org: Client, partido: Partido) -> None:
    html = org.get(f"/partidos/{partido.pk}/reprogramar/").content.decode()
    encontrados = botones(html, "Ver propuestas")
    assert encontrados and all(CALCULANDO in b for b in encontrados)


@pytest.mark.django_db
def test_ver_propuestas_de_un_bloqueo(org: Client, torneo: Torneo, bloqueo: Bloqueo) -> None:
    html = org.get(f"/torneos/{torneo.pk}/acf/").content.decode()
    encontrados = botones(html, "Ver propuestas")
    assert encontrados and all(CALCULANDO in b for b in encontrados)


@pytest.mark.django_db
def test_volver_a_calcular(org: Client, bloqueo: Bloqueo) -> None:
    corrida = calcular_propuestas(bloqueo, None)
    html = org.get(f"/corridas/{corrida.pk}/propuestas/").content.decode()
    encontrados = botones(html, "Volver a calcular")
    assert encontrados and all(CALCULANDO in b for b in encontrados)
    # Aplicar o dar W.O. no calculan: siguen como siempre.
    assert all(CALCULANDO not in b for b in botones(html, "Aplicar"))


@pytest.mark.django_db
def test_programar(org: Client, torneo: Torneo) -> None:
    html = org.get(f"/torneos/{torneo.pk}/programar/").content.decode()
    inicio = html.index(f'hx-post="/torneos/{torneo.pk}/programar/"')
    formulario = html[inicio : html.index("</form>", inicio)]
    encontrados = re.findall(r"<button[^>]*>", formulario)
    assert encontrados and all(CALCULANDO in b for b in encontrados)


@pytest.mark.django_db
def test_la_confirmacion_de_programar(org: Client, torneo: Torneo) -> None:
    # Con partidos ya programados, programar todo pide confirmación: ese botón también calcula.
    html = org.post(
        f"/torneos/{torneo.pk}/programar/", {"modo": "todo"}, headers={"HX-Request": "true"}
    ).content.decode()
    encontrados = botones(html, "Volver a programar")
    assert encontrados and all(CALCULANDO in b for b in encontrados)


def test_ui_js_bloquea_los_botones_que_calculan() -> None:
    js = (Path(settings.RAIZ) / "src/torneo/static/js/ui.js").read_text()
    assert "dataset.calculando" in js and "submitter" in js
