"""El usuario se escribe sin importar mayúsculas: el teclado del celular pone la primera sola."""

from io import StringIO

import pytest
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command

CLAVE = "Cancha-Sintetica-2026!"


@pytest.mark.django_db
@pytest.mark.parametrize("escrito", ["sebastian", "Sebastian", "SEBASTIAN", "  sebastian "])
def test_entra_aunque_cambien_las_mayusculas_del_usuario(escrito: str) -> None:
    User.objects.create_user("sebastian", password=CLAVE)
    assert authenticate(username=escrito, password=CLAVE) is not None


@pytest.mark.django_db
def test_la_contrasena_si_distingue_mayusculas() -> None:
    User.objects.create_user("sebastian", password=CLAVE)
    assert authenticate(username="Sebastian", password=CLAVE.lower()) is None


@pytest.mark.django_db
def test_crear_usuario_guarda_el_nombre_en_minusculas(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RONDO_CLAVE_USUARIO", CLAVE)
    call_command("crear_usuario", "Organizador", stdout=StringIO())
    assert User.objects.filter(username="organizador").exists()


@pytest.mark.django_db
def test_crear_usuario_rechaza_un_nombre_repetido_con_otras_mayusculas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RONDO_CLAVE_USUARIO", CLAVE)
    User.objects.create_user("organizador", password=CLAVE)
    with pytest.raises(CommandError, match="ya existe"):
        call_command("crear_usuario", "Organizador", stdout=StringIO())
