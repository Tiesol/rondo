"""T6.2: personas y roles desde la app, sin terminal (R6)."""

import logging
import re

import pytest
from django.contrib.auth.models import Group, User
from django.test import Client

from torneo.permisos import MESA, ORGANIZACION, nombre_del_rol


def entrar(client: Client, grupo: str, nombre: str = "seba") -> User:
    usuario = User.objects.create_user(nombre, password="Clave-Vieja-2026!")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return usuario


@pytest.mark.django_db
def test_la_organizacion_agrega_a_alguien_y_ve_la_clave_una_vez(
    client: Client, caplog: pytest.LogCaptureFixture
) -> None:
    entrar(client, ORGANIZACION)
    with caplog.at_level(logging.DEBUG):
        respuesta = client.post(
            "/personas/nueva/", {"usuario": "Mesa1", "nombre": "Mesa uno", "rol": "mesa"}
        )
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    clave = re.search(r'data-clave="([^"]+)"', html)
    assert clave is not None
    nuevo = User.objects.get(username="mesa1")
    assert nuevo.check_password(clave.group(1))
    assert not nuevo.is_staff
    assert nombre_del_rol(nuevo) == MESA
    assert clave.group(1) not in caplog.text
    assert respuesta.wsgi_request.sensitive_post_parameters == "__ALL__"  # type: ignore[attr-defined]
    # Volver a la lista no la muestra de nuevo.
    assert clave.group(1) not in client.get("/mas/").content.decode()


@pytest.mark.django_db
def test_un_usuario_repetido_da_error(client: Client) -> None:
    entrar(client, ORGANIZACION)
    User.objects.create_user("mesa1")
    respuesta = client.post("/personas/nueva/", {"usuario": "MESA1", "nombre": "", "rol": "mesa"})
    assert "Ya existe" in respuesta.content.decode()


@pytest.mark.django_db
def test_la_organizacion_cambia_el_rol_de_otra_persona(client: Client) -> None:
    entrar(client, ORGANIZACION)
    otra = User.objects.create_user("ana")
    otra.groups.add(Group.objects.get(name=MESA))
    client.post(f"/personas/{otra.pk}/rol/", {"rol": "organizacion"})
    assert nombre_del_rol(otra) == ORGANIZACION


@pytest.mark.django_db
def test_nadie_se_cambia_el_rol_a_si_mismo(client: Client) -> None:
    yo = entrar(client, ORGANIZACION)
    respuesta = client.post(f"/personas/{yo.pk}/rol/", {"rol": "mesa"}, follow=True)
    assert "No puedes cambiar tu propio rol" in respuesta.content.decode()
    assert nombre_del_rol(yo) == ORGANIZACION


@pytest.mark.django_db
def test_la_mesa_no_gestiona_personas(client: Client) -> None:
    entrar(client, MESA)
    assert client.get("/personas/nueva/").status_code == 403
    otra = User.objects.create_user("ana")
    assert client.post(f"/personas/{otra.pk}/rol/", {"rol": "organizacion"}).status_code == 403


@pytest.mark.django_db
def test_cualquiera_cambia_su_contrasenia(client: Client) -> None:
    yo = entrar(client, MESA)
    assert "Cambiar mi contraseña" in client.get("/mas/").content.decode()
    assert client.get("/cuentas/password_change/").status_code == 200
    respuesta = client.post(
        "/cuentas/password_change/",
        {
            "old_password": "Clave-Vieja-2026!",
            "new_password1": "Cancha-Nueva-2026!",
            "new_password2": "Cancha-Nueva-2026!",
        },
    )
    assert respuesta.status_code == 302
    yo.refresh_from_db()
    assert yo.check_password("Cancha-Nueva-2026!")
