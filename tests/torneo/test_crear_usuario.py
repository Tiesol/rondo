"""El comando crear_usuario toma la contraseña del entorno y nunca la muestra (T0.3)."""

from io import StringIO

import pytest
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command

CLAVE = "Cancha-Sintetica-2026!"


@pytest.mark.django_db
def test_crea_un_usuario_de_la_organizacion_sin_mostrar_la_clave(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RONDO_CLAVE_USUARIO", CLAVE)
    salida = StringIO()

    call_command("crear_usuario", "organizador", stdout=salida, stderr=salida)

    usuario = User.objects.get(username="organizador")
    # TU.2: el admin es solo para el superusuario; la organización usa las pantallas.
    assert not usuario.is_staff
    assert not usuario.is_superuser
    assert usuario.groups.filter(name="Organización").exists()
    assert usuario.check_password(CLAVE)
    assert CLAVE not in salida.getvalue()


@pytest.mark.django_db
def test_admin_crea_un_superusuario(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RONDO_CLAVE_USUARIO", CLAVE)

    call_command("crear_usuario", "sebastian", "--admin", stdout=StringIO())

    sebastian = User.objects.get(username="sebastian")
    assert sebastian.is_superuser
    assert sebastian.is_staff


@pytest.mark.django_db
def test_falla_si_falta_la_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RONDO_CLAVE_USUARIO", raising=False)
    with pytest.raises(CommandError, match="RONDO_CLAVE_USUARIO"):
        call_command("crear_usuario", "organizador")


@pytest.mark.django_db
def test_rechaza_una_clave_debil(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RONDO_CLAVE_USUARIO", "12345678")
    with pytest.raises(CommandError):
        call_command("crear_usuario", "organizador")
    assert not User.objects.filter(username="organizador").exists()
