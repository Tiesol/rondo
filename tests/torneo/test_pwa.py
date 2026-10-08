"""T5.8: la app se instala en el celular y funciona solo con conexión."""

import json
from pathlib import Path

import pytest
from django.test import Client

ICONOS = Path(__file__).resolve().parents[2] / "src" / "torneo" / "static" / "iconos"


@pytest.mark.django_db
def test_el_manifest_se_sirve_sin_login(client: Client) -> None:
    respuesta = client.get("/manifest.webmanifest")
    assert respuesta.status_code == 200
    assert respuesta["Content-Type"].startswith("application/manifest+json")
    manifest = json.loads(respuesta.content)
    assert manifest["start_url"] == "/"
    assert manifest["display"] == "standalone"
    assert manifest["lang"] == "es"
    assert "JMP" in manifest["name"]
    tamanios = {icono["sizes"] for icono in manifest["icons"]}
    assert {"192x192", "512x512"} <= tamanios
    for icono in manifest["icons"]:
        assert (ICONOS / Path(icono["src"]).name).is_file()


@pytest.mark.django_db
def test_el_service_worker_no_guarda_datos(client: Client) -> None:
    respuesta = client.get("/sw.js")
    assert respuesta.status_code == 200
    assert "javascript" in respuesta["Content-Type"]
    codigo = respuesta.content.decode()
    assert "Sin conexión" in codigo
    assert "caches.open" not in codigo  # funciona solo con conexión: no guarda nada


@pytest.mark.django_db
def test_la_base_enlaza_el_manifest_y_registra_el_service_worker(client: Client) -> None:
    html = client.get("/cuentas/login/").content.decode()
    assert '<link rel="manifest" href="/manifest.webmanifest">' in html
    assert 'name="theme-color"' in html
    assert "apple-touch-icon" in html
