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


def test_los_directorios_de_estaticos_existen_en_un_clon_nuevo() -> None:
    # Revisión externa, punto 6: sin assets/ en el repo, `check --deploy` da staticfiles.W004
    # en un clon recién hecho, antes de compilar Tailwind.
    from django.conf import settings

    versionados = subprocess.run(
        ["git", "ls-files", *(str(d.relative_to(RAIZ)) for d in settings.STATICFILES_DIRS)],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    for directorio in settings.STATICFILES_DIRS:
        rel = str(directorio.relative_to(RAIZ))
        assert any(f.startswith(rel + "/") for f in versionados), f"{rel}/ no está en el repo"


def _leer(*expresiones: str, entorno: dict[str, str]) -> list[str]:
    resultado = _manage(
        "shell",
        "-c",
        "from django.conf import settings; " + "; ".join(f"print(repr({e}))" for e in expresiones),
        entorno=PRODUCCION | {"SECRET_KEY": secrets.token_urlsafe(50)} | entorno,
    )
    assert resultado.returncode == 0, resultado.stderr
    return resultado.stdout.strip().splitlines()[-len(expresiones) :]


SEGURIDAD = (
    "settings.SECURE_SSL_REDIRECT",
    "settings.SESSION_COOKIE_SECURE",
    "settings.CSRF_COOKIE_SECURE",
    "settings.SECURE_HSTS_SECONDS",
)


def test_la_copia_local_como_render_se_abre_por_http_desde_el_celular() -> None:
    # T13.38: compose.yaml levanta la imagen con DEBUG=false en la red de la casa, sin TLS.
    # Sin esto, redirige a https y el navegador no guarda las cookies "Secure" por http.
    local = _leer(*SEGURIDAD, entorno={"RONDO_HTTP_LOCAL": "true"})
    assert local == ["False", "False", "False", "0"]


def test_sin_la_variable_produccion_sigue_exigiendo_https() -> None:
    assert _leer(*SEGURIDAD, entorno={}) == ["True", "True", "True", str(60 * 60 * 24 * 365)]


def test_la_variable_local_no_vale_en_render() -> None:
    resultado = _manage(
        "check",
        entorno=PRODUCCION
        | {
            "SECRET_KEY": secrets.token_urlsafe(50),
            "RONDO_HTTP_LOCAL": "true",
            "RENDER_EXTERNAL_HOSTNAME": "rondo-demo.onrender.com",
        },
    )
    assert resultado.returncode != 0
    assert "RONDO_HTTP_LOCAL" in resultado.stderr
