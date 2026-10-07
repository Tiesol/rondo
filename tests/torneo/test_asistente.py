"""TU.4: crear el torneo con el asistente de 4 pasos, desde la plantilla del reglamento."""

from collections.abc import Callable
from datetime import time
from typing import Any

import pytest
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import Reglas
from torneo.models import Franja, Torneo
from torneo.permisos import MESA, ORGANIZACION

URL = "/torneos/nuevo/"


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


def campos_iniciales(client: Client, paso: int) -> dict[str, Any]:
    """Lo que el navegador mandaría sin cambiar nada en el paso."""
    formulario = client.get(f"{URL}{paso}/").context["form"]
    datos: dict[str, Any] = {}
    for nombre, campo in formulario.fields.items():
        valor = formulario[nombre].value()
        if isinstance(valor, bool):
            if valor:
                datos[nombre] = "on"
        elif isinstance(valor, (list, tuple)):
            if type(campo).__name__ == "ParDeNumeros":
                datos[f"{nombre}_0"], datos[f"{nombre}_1"] = valor
            else:
                datos[nombre] = list(valor)
        elif valor is not None:
            datos[nombre] = valor
    return datos


Cambio = dict[str, Any] | Callable[[dict[str, Any]], dict[str, Any]]


def recorrer(client: Client, cambios: dict[int, Cambio] | None = None) -> Any:
    """Recorre los 4 pasos. Un cambio puede ser una función de lo que muestra el paso."""
    respuesta = None
    for paso in (1, 2, 3, 4):
        datos = campos_iniciales(client, paso)
        cambio = (cambios or {}).get(paso, {})
        datos.update(cambio(datos) if callable(cambio) else cambio)
        datos = {k: v for k, v in datos.items() if v is not None}
        respuesta = client.post(f"{URL}{paso}/", datos)
        assert respuesta.status_code == 302, respuesta.context["form"].errors
    return respuesta


@pytest.mark.django_db
def test_sin_cambiar_nada_crea_lo_mismo_que_cargar_config(org: Client) -> None:
    respuesta = recorrer(org)
    torneo = Torneo.objects.get()
    assert (torneo.nombre, torneo.anio, torneo.edicion) == ("JMP CUP 2026", 2026, 5)
    assert torneo.categorias.count() == 23
    assert torneo.canchas.count() == 5
    assert torneo.franjas.count() == 15
    assert torneo.reglas == Reglas().model_dump(mode="json")
    assert respuesta["Location"] == "/"
    assert "asistente" not in org.session


@pytest.mark.django_db
def test_destildar_una_categoria_y_cambiar_un_horario_se_refleja(org: Client) -> None:
    def sin_sub_5(datos: dict[str, Any]) -> dict[str, Any]:
        return {"niveles": [c for c in datos["niveles"] if c != "Sub 5|unico"]}

    recorrer(org, {2: sin_sub_5, 3: {"sabado_inicio": "09:00"}})
    torneo = Torneo.objects.get()
    assert not torneo.categorias.filter(categoria="Sub 5").exists()
    assert torneo.categorias.count() == 22
    sabados = [f for f in torneo.franjas.all() if timezone.localtime(f.inicio).weekday() == 5]
    assert sabados
    for franja in sabados:
        local = timezone.localtime(franja.inicio)
        assert local.time() == time(9, 0)
        assert franja.tipo == Franja.Tipo.REGULAR


@pytest.mark.django_db
def test_apagar_un_dia_lo_saca_de_las_franjas(org: Client) -> None:
    recorrer(org, {3: {"viernes_activo": None}})
    assert Torneo.objects.get().franjas.count() == 10


@pytest.mark.django_db
def test_volver_atras_no_pierde_lo_cargado(org: Client) -> None:
    datos = campos_iniciales(org, 1) | {"nombre": "Copa de Prueba"}
    org.post(f"{URL}1/", datos)
    org.post(f"{URL}2/", campos_iniciales(org, 2) | {"ir": "atras"})
    assert org.get(f"{URL}1/").context["form"]["nombre"].value() == "Copa de Prueba"


@pytest.mark.django_db
def test_no_se_salta_pasos(org: Client) -> None:
    respuesta = org.get(f"{URL}3/")
    assert respuesta.status_code == 302
    assert respuesta["Location"] == f"{URL}1/"


@pytest.mark.django_db
def test_no_pisa_un_torneo_que_ya_existe(org: Client) -> None:
    recorrer(org)
    respuesta = org.post(f"{URL}1/", campos_iniciales(org, 1))
    assert respuesta.status_code == 200
    assert "Ya existe" in str(respuesta.context["form"].errors)


@pytest.mark.django_db
def test_la_mesa_no_crea_torneos(client: Client) -> None:
    usuario = User.objects.create_user("mesa", password="x")
    usuario.groups.add(Group.objects.get(name=MESA))
    client.force_login(usuario)
    respuesta = client.get(f"{URL}1/")
    assert respuesta.status_code == 403
    assert "Solo la organización puede crear torneos" in respuesta.content.decode()


@pytest.mark.django_db
def test_mas_ofrece_crear_un_torneo_solo_a_la_organizacion(org: Client) -> None:
    assert f'href="{URL}"' in org.get("/mas/").content.decode()
