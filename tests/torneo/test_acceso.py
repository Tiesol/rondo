"""Todo pide login (T0.3, SPEC "Criterios de éxito" 7)."""

import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.mark.django_db
def test_un_anonimo_va_al_login(client: Client) -> None:
    respuesta = client.get("/")
    assert respuesta.status_code == 302
    assert respuesta["Location"] == "/cuentas/login/?next=/"


@pytest.mark.django_db
def test_el_admin_tambien_pide_login(client: Client) -> None:
    respuesta = client.get("/admin/")
    assert respuesta.status_code == 302
    assert "login" in respuesta["Location"]


@pytest.mark.django_db
def test_la_pagina_de_login_se_ve_sin_sesion_y_en_espanol(client: Client) -> None:
    respuesta = client.get("/cuentas/login/")
    assert respuesta.status_code == 200
    assert "Iniciar sesión" in respuesta.content.decode()


@pytest.mark.django_db
def test_con_sesion_se_ve_el_inicio(client: Client) -> None:
    client.force_login(User.objects.create_user("mesa", password="x"))
    respuesta = client.get("/")
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert 'name="viewport"' in html
    assert "htmx.min.js" in html


@pytest.mark.django_db
def test_cerrar_sesion_vuelve_a_pedir_login(client: Client) -> None:
    client.force_login(User.objects.create_user("mesa", password="x"))
    respuesta = client.post("/cuentas/logout/")
    assert respuesta.status_code == 302
    assert client.get("/").status_code == 302
