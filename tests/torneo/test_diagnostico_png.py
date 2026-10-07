"""T0.7: página de prueba del PNG, solo para staff y sin datos personales."""

import pytest
from django.contrib.auth.models import User
from django.test import Client

URL = "/diagnostico/png/"


@pytest.mark.django_db
def test_un_anonimo_va_al_login(client: Client) -> None:
    assert client.get(URL)["Location"].startswith("/cuentas/login/")


@pytest.mark.django_db
def test_un_usuario_sin_staff_no_puede_verla(client: Client) -> None:
    client.force_login(User.objects.create_user("mesa", password="x"))
    assert client.get(URL).status_code == 403


@pytest.mark.django_db
def test_el_staff_ve_el_calendario_de_prueba_listo_para_exportar(client: Client) -> None:
    client.force_login(User.objects.create_user("org", password="x", is_staff=True))
    respuesta = client.get(URL)
    html = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert "modern-screenshot.js" in html
    assert "js/exportar.js" in html
    assert 'id="calendario-exportable"' in html
    assert "River Plate" in html
