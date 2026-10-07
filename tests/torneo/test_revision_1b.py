"""Hallazgos de la revisión de cierre de la fase 1b (ver PROGRESO.md)."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion

HISTORIAL = {"HX-Request": "true", "HX-History-Restore-Request": "true"}


def entrar(client: Client, grupo: str) -> Client:
    usuario = User.objects.create_user(grupo[:4], password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    torneo.publico = True
    torneo.save()
    return torneo


@pytest.mark.django_db
def test_volver_con_el_navegador_trae_la_pagina_entera_en_torneo(
    client: Client, torneo: Torneo
) -> None:
    """HTMX pide la página entera cuando no la tiene guardada en su historial."""
    categoria = torneo.categorias.first()
    assert categoria is not None
    html = entrar(client, MESA).get(f"/torneo/{categoria.pk}/equipos/", headers=HISTORIAL)
    assert "<html" in html.content.decode()


@pytest.mark.django_db
def test_volver_con_el_navegador_trae_la_pagina_entera_en_publico(
    client: Client, torneo: Torneo
) -> None:
    categoria = torneo.categorias.first()
    assert categoria is not None
    html = client.get(f"/t/{torneo.pk}/{categoria.pk}/partidos/", headers=HISTORIAL)
    assert "<html" in html.content.decode()


@pytest.mark.django_db
def test_el_asistente_no_pisa_un_torneo_creado_mientras_tanto(client: Client) -> None:
    org = entrar(client, ORGANIZACION)
    for paso in (1, 2, 3):
        formulario = org.get(f"/torneos/nuevo/{paso}/").context["form"]
        datos = {
            n: formulario[n].value()
            for n in formulario.fields
            if formulario[n].value() not in (None, False)
        }
        org.post(f"/torneos/nuevo/{paso}/", datos)
    # Alguien carga el mismo torneo desde la terminal antes de que termine el asistente.
    existente = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    existente.reglas = existente.reglas | {"max_partidos_por_dia": 3}
    existente.save()

    formulario = org.get("/torneos/nuevo/4/").context["form"]
    datos = {}
    for nombre in formulario.fields:
        valor = formulario[nombre].value()
        if valor is True:
            datos[nombre] = "on"
        elif isinstance(valor, (list, tuple)):
            datos[f"{nombre}_0"], datos[f"{nombre}_1"] = valor
        elif valor not in (None, False):
            datos[nombre] = valor
    respuesta = org.post("/torneos/nuevo/4/", datos)
    assert respuesta.status_code == 200
    assert "Ya existe" in str(respuesta.context["form"].non_field_errors())
    existente.refresh_from_db()
    assert existente.reglas["max_partidos_por_dia"] == 3


@pytest.mark.django_db
def test_mas_no_hace_una_consulta_por_persona(
    client: Client, django_assert_max_num_queries: object
) -> None:
    org = entrar(client, ORGANIZACION)
    org.get("/mas/")
    for i in range(15):
        User.objects.create_user(f"persona{i}").groups.add(Group.objects.get(name=MESA))
    with django_assert_max_num_queries(12):  # type: ignore[operator]
        org.get("/mas/")


@pytest.mark.django_db
def test_con_sesion_el_login_lleva_al_inicio(client: Client) -> None:
    respuesta = entrar(client, MESA).get("/cuentas/login/")
    assert respuesta.status_code == 302
    assert respuesta["Location"] == "/"


@pytest.mark.django_db
def test_la_pagina_404_explica_y_ofrece_volver(client: Client) -> None:
    respuesta = client.get("/t/999/")
    assert respuesta.status_code == 404
    assert "No encontramos esta página" in respuesta.content.decode()
