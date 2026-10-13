"""T8.1: el almacenamiento de imágenes se conecta por variables de entorno (Cloudflare R2).

Sin las variables, la app funciona igual: en desarrollo y en los tests usa el disco; en
producción o en la demo, la subida de imágenes queda desactivada con un aviso.
"""

import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

import pytest
from django.template.loader import render_to_string

RAIZ = Path(__file__).resolve().parents[2]
PRODUCCION = {
    "DEBUG": "false",
    "ALLOWED_HOSTS": "rondo.example.com",
    "DATABASE_URL": "postgres://rondo:rondo@localhost:5432/rondo",
}


def _manage(*args: str, entorno: dict[str, str]) -> subprocess.CompletedProcess[str]:
    base = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME"}}
    base["RONDO_ENV_FILE"] = ""  # sin .env: la prueba controla todas las variables
    return subprocess.run(
        [sys.executable, str(RAIZ / "manage.py"), *args],
        env=base | entorno,
        capture_output=True,
        text=True,
        check=False,
    )


R2 = {
    "R2_ACCOUNT_ID": "cuenta-inventada",
    "R2_ACCESS_KEY_ID": "clave-inventada",
    "R2_SECRET_ACCESS_KEY": "secreto-inventado",
    "R2_BUCKET": "rondo-prueba",
}
LEER = (
    "import json; from django.conf import settings; "
    "print(json.dumps({'storage': settings.STORAGES['default'], "
    "'disponibles': settings.IMAGENES_DISPONIBLES}))"
)


def _settings(entorno: dict[str, str]) -> dict[str, object]:
    resultado = _manage("shell", "-c", LEER, entorno=entorno)
    assert resultado.returncode == 0, resultado.stderr
    datos: dict[str, object] = json.loads(resultado.stdout.strip().splitlines()[-1])
    return datos


def test_con_las_cuatro_variables_las_imagenes_van_a_r2_privado() -> None:
    datos = _settings(PRODUCCION | R2 | {"SECRET_KEY": secrets.token_urlsafe(50)})
    storage = datos["storage"]
    assert isinstance(storage, dict)
    assert storage["BACKEND"] == "storages.backends.s3.S3Storage"
    opciones = storage["OPTIONS"]
    assert opciones["bucket_name"] == "rondo-prueba"
    assert opciones["endpoint_url"] == "https://cuenta-inventada.r2.cloudflarestorage.com"
    assert opciones["default_acl"] is None  # el bucket es privado
    assert opciones["querystring_auth"] is True  # URL firmadas que vencen
    assert opciones["file_overwrite"] is False
    assert datos["disponibles"] is True


def test_en_produccion_sin_r2_la_subida_queda_desactivada() -> None:
    datos = _settings(PRODUCCION | {"SECRET_KEY": secrets.token_urlsafe(50)})
    assert datos["disponibles"] is False


def test_con_una_variable_a_medias_tampoco() -> None:
    a_medias = {k: v for k, v in R2.items() if k != "R2_BUCKET"}
    datos = _settings(PRODUCCION | a_medias | {"SECRET_KEY": secrets.token_urlsafe(50)})
    assert datos["disponibles"] is False


def test_en_desarrollo_usa_el_disco() -> None:
    datos = _settings(
        {"DEBUG": "true", "SECRET_KEY": "x", "DATABASE_URL": PRODUCCION["DATABASE_URL"]}
    )
    storage = datos["storage"]
    assert isinstance(storage, dict)
    assert storage["BACKEND"] == "django.core.files.storage.FileSystemStorage"
    assert datos["disponibles"] is True


def test_produccion_con_r2_pasa_check_deploy() -> None:
    resultado = _manage(
        "check",
        "--deploy",
        "--fail-level",
        "WARNING",
        entorno=PRODUCCION | R2 | {"SECRET_KEY": secrets.token_urlsafe(50)},
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


@pytest.mark.parametrize("disponibles", [True, False])
def test_el_campo_de_imagen_avisa_si_falta_conectar(disponibles: bool) -> None:
    html = render_to_string(
        "parciales/campo_imagen.html",
        {"nombre": "escudo", "etiqueta": "Escudo", "imagenes_disponibles": disponibles},
    )
    assert ("Falta conectar el almacenamiento de imágenes" in html) is not disponibles
    assert ("disabled" in html) is not disponibles
