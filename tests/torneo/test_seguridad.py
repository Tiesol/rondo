"""T6.3: revisión de seguridad. Acceso en cada URL, encabezados y límite de intentos."""

import re
from typing import Any

import pytest
from django.contrib.auth.models import Group, User
from django.test import Client
from django.urls import URLPattern, URLResolver, get_resolver

from torneo.permisos import MESA

# Las únicas que se abren sin sesión: el login, la página pública y lo que pide la PWA.
PUBLICAS = {"login", "publico", "publico-categoria", "manifest", "service-worker"}
# Las de la organización: la mesa recibe un 403 (con el aviso del rol).
DE_LA_ORGANIZACION = [
    "/torneos/nuevo/1/",
    "/torneos/1/reglas/",
    "/torneos/1/programar/",
    "/torneos/1/acf/",
    "/escuela/",
    "/personas/nueva/",
    "/partidos/1/mover/",
    "/corridas/1/propuestas/",
]


def rutas() -> list[tuple[str, str]]:
    """(nombre, URL de ejemplo) de cada ruta de la app, sin el admin."""
    encontradas = []

    def recorrer(patrones: list[Any], prefijo: str) -> None:
        for patron in patrones:
            texto = prefijo + str(patron.pattern)
            if isinstance(patron, URLResolver):
                if not texto.startswith("admin/"):
                    recorrer(patron.url_patterns, texto)
            elif isinstance(patron, URLPattern) and patron.name:
                ejemplo = re.sub(r"<int:\w+>", "1", texto)
                ejemplo = re.sub(r"<str:fecha>", "2026-10-24", ejemplo)
                ejemplo = re.sub(r"<str:\w+>", "x", ejemplo)
                encontradas.append((patron.name, "/" + ejemplo))

    recorrer(get_resolver().url_patterns, "")
    return encontradas


@pytest.mark.django_db
@pytest.mark.parametrize(("nombre", "url"), rutas(), ids=lambda v: str(v))
def test_toda_url_pide_login_salvo_las_publicas(client: Client, nombre: str, url: str) -> None:
    respuesta = client.get(url)
    if nombre in PUBLICAS:
        assert respuesta.status_code in (200, 302, 404)
        if respuesta.status_code == 302:
            assert "/cuentas/login/" not in respuesta["Location"]
    else:
        assert respuesta.status_code == 302, url
        assert respuesta["Location"].startswith("/cuentas/login/"), url


@pytest.mark.django_db
@pytest.mark.parametrize("url", DE_LA_ORGANIZACION)
def test_la_mesa_recibe_403_en_lo_de_la_organizacion(client: Client, url: str) -> None:
    usuario = User.objects.create_user("mesa", password="x")
    usuario.groups.add(Group.objects.get(name=MESA))
    client.force_login(usuario)
    assert client.get(url).status_code == 403


@pytest.mark.django_db
def test_la_recuperacion_de_clave_por_correo_no_esta(client: Client) -> None:
    """No hay correo configurado: esas rutas solo serían superficie de ataque."""
    for url in ("/cuentas/password_reset/", "/cuentas/reset/done/"):
        assert client.get(url).status_code == 404


@pytest.mark.django_db
def test_encabezados_de_seguridad(client: Client) -> None:
    respuesta = client.get("/cuentas/login/")
    csp = respuesta["Content-Security-Policy"]
    for directiva in (
        "default-src 'self'",
        "script-src 'self'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
        "base-uri 'self'",
    ):
        assert directiva in csp
    assert "unsafe-inline" not in csp.split("script-src")[1].split(";")[0]
    assert "camera=()" in respuesta["Permissions-Policy"]
    assert respuesta["X-Frame-Options"] == "DENY"
    assert respuesta["X-Content-Type-Options"] == "nosniff"


@pytest.mark.django_db
def test_muchos_intentos_fallidos_frenan_el_login(client: Client) -> None:
    User.objects.create_user("seba", password="Cancha-Sintetica-2026!")
    for i in range(10):
        client.post("/cuentas/login/", {"username": "seba", "password": f"mal{i}"})
    respuesta = client.post(
        "/cuentas/login/", {"username": "seba", "password": "Cancha-Sintetica-2026!"}
    )
    assert respuesta.status_code == 429
    assert "Demasiados intentos" in respuesta.content.decode()


@pytest.mark.django_db
def test_pocos_intentos_fallidos_no_frenan(client: Client) -> None:
    User.objects.create_user("seba", password="Cancha-Sintetica-2026!")
    for i in range(3):
        client.post("/cuentas/login/", {"username": "seba", "password": f"mal{i}"})
    respuesta = client.post(
        "/cuentas/login/", {"username": "seba", "password": "Cancha-Sintetica-2026!"}
    )
    assert respuesta.status_code == 302


def test_hay_pagina_500_que_no_depende_de_la_base() -> None:
    from django.template.loader import get_template

    html = get_template("500.html").render({})
    assert "Algo salió mal" in html
