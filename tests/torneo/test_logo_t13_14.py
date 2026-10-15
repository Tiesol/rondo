"""T13.14: el logo de Escuela en todos lados (barra, menú lateral, login y página pública) y el
favicon. Sin logo, la sigla. Imagen inventada."""

import io

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from dominio.config import cargar_config
from torneo.models import Organizador, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.imagenes import reemplazar_imagen


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    torneo.publico = True
    torneo.save()
    return torneo


def con_logo() -> str:
    salida = io.BytesIO()
    Image.new("RGB", (300, 300), (10, 40, 90)).save(salida, "PNG")
    organizador = Organizador.actual()
    reemplazar_imagen(
        organizador.logo, SimpleUploadedFile("logo.png", salida.getvalue()), tipo="logo"
    )
    return f"/imagen/logo/{organizador.pk}/"


def paginas(client: Client, torneo: Torneo) -> dict[str, str]:
    categoria = torneo.categorias.first()
    assert categoria is not None
    publica = client.get(f"/t/{torneo.pk}/{categoria.pk}/partidos/").content.decode()
    login = client.get("/cuentas/login/").content.decode()
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return {"login": login, "pública": publica, "inicio": client.get("/").content.decode()}


@pytest.mark.django_db
def test_con_logo_ninguna_pantalla_muestra_la_sigla(client: Client, torneo: Torneo) -> None:
    url = con_logo()
    sigla = Organizador.actual().sigla
    for nombre, html in paginas(client, torneo).items():
        assert url in html, nombre
        assert f'aria-hidden="true">{sigla}</span>' not in html, nombre
        assert f'<link rel="icon" href="{url}' in html, nombre


@pytest.mark.django_db
def test_sin_logo_la_sigla_y_el_icono_fijo(client: Client, torneo: Torneo) -> None:
    sigla = Organizador.actual().sigla
    for nombre, html in paginas(client, torneo).items():
        assert f">{sigla}</span>" in html, nombre
        assert '<link rel="icon" href="/static/iconos/icono-192' in html, nombre
