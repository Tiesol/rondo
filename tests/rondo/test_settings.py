"""Los settings de producción: modo seguro y sin valores por defecto inseguros (T0.2)."""

import os
import secrets
import subprocess
import sys
from pathlib import Path

import pytest
from django.db import connection

RAIZ = Path(__file__).resolve().parents[2]


def _manage(*args: str, entorno: dict[str, str]) -> subprocess.CompletedProcess[str]:
    base = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME"}}
    # Sin .env: la prueba controla todas las variables.
    base["RONDO_ENV_FILE"] = ""
    return subprocess.run(
        [sys.executable, str(RAIZ / "manage.py"), *args],
        env=base | entorno,
        capture_output=True,
        text=True,
        check=False,
    )


PRODUCCION = {
    "DEBUG": "false",
    "ALLOWED_HOSTS": "rondo.example.com",
    "DATABASE_URL": "postgres://rondo:rondo@localhost:5432/rondo",
}


def test_produccion_pasa_check_deploy_sin_advertencias() -> None:
    resultado = _manage(
        "check",
        "--deploy",
        "--fail-level",
        "WARNING",
        entorno=PRODUCCION | {"SECRET_KEY": secrets.token_urlsafe(50)},
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def test_produccion_sin_secret_key_no_arranca() -> None:
    resultado = _manage("check", entorno=PRODUCCION)
    assert resultado.returncode != 0
    assert "SECRET_KEY" in resultado.stderr


@pytest.mark.django_db
def test_la_base_local_responde() -> None:
    with connection.cursor() as cursor:
        cursor.execute("select 1")
        assert cursor.fetchone() == (1,)


def test_acepta_la_direccion_que_asigna_render() -> None:
    resultado = _manage(
        "shell",
        "-c",
        "from django.conf import settings; "
        "print(settings.ALLOWED_HOSTS); print(settings.CSRF_TRUSTED_ORIGINS)",
        entorno=PRODUCCION
        | {
            "SECRET_KEY": secrets.token_urlsafe(50),
            "RENDER_EXTERNAL_HOSTNAME": "rondo-demo.onrender.com",
        },
    )
    assert resultado.returncode == 0, resultado.stderr
    hosts, origenes = resultado.stdout.strip().splitlines()[-2:]
    assert "rondo-demo.onrender.com" in hosts
    assert "https://rondo-demo.onrender.com" in origenes


def test_produccion_sin_database_url_falla_con_un_mensaje_claro() -> None:
    resultado = _manage(
        "check",
        entorno={"DEBUG": "false", "ALLOWED_HOSTS": "x", "SECRET_KEY": secrets.token_urlsafe(50)},
    )
    assert resultado.returncode != 0
    assert "Falta la variable de entorno DATABASE_URL" in resultado.stderr
