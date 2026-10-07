"""TU.7: datos de la escuela (nombre y colores), sin admin, y sus colores en la interfaz."""

import pytest
from django.contrib.auth.models import Group, User
from django.test import Client

from torneo.colores import contraste, texto_sobre
from torneo.models import Organizador
from torneo.permisos import MESA, ORGANIZACION

URL = "/escuela/"


def entrar(client: Client, grupo: str) -> Client:
    usuario = User.objects.create_user(grupo[:4], password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


def test_contraste_de_colores() -> None:
    assert contraste("#ffffff", "#000000") == pytest.approx(21, abs=0.01)
    assert contraste("#0d2440", "#ffffff") > 4.5
    assert contraste("#f2cf3a", "#ffffff") < 2


def test_el_texto_sobre_un_color_es_el_que_mas_se_lee() -> None:
    assert texto_sobre("#f2cf3a") == "#0d2440"
    assert texto_sobre("#0d2440") == "#ffffff"


@pytest.mark.django_db
def test_los_colores_por_defecto_son_los_de_la_jmp_cup() -> None:
    organizador = Organizador.actual()
    assert (organizador.color_primario, organizador.color_acento) == ("#0d2440", "#f2cf3a")


@pytest.mark.django_db
def test_la_base_pinta_con_los_colores_del_organizador(client: Client) -> None:
    Organizador.objects.update_or_create(
        pk=1, defaults={"color_primario": "#7a1f2b", "color_acento": "#e0e0e0"}
    )
    html = entrar(client, MESA).get("/").content.decode()
    assert "--marca: #7a1f2b" in html
    assert "--acento: #e0e0e0" in html
    assert "--sobre-acento: #0d2440" in html


@pytest.mark.django_db
def test_la_organizacion_cambia_el_nombre_y_se_ve_en_todas_partes(client: Client) -> None:
    org = entrar(client, ORGANIZACION)
    datos = {"nombre": "Academia Prueba", "color_primario": "#0d2440", "color_acento": "#f2cf3a"}
    assert org.post(URL, datos).status_code == 302
    assert "Academia Prueba" in org.get("/").content.decode()
    assert "Academia Prueba" in Client().get("/cuentas/login/").content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("campo", "valor", "mensaje"),
    [
        ("color_primario", "verde", "hexadecimal"),
        ("color_acento", "#12", "hexadecimal"),
        ("color_primario", "#f2cf3a", "más oscuro"),
    ],
)
def test_un_color_invalido_muestra_el_error_en_el_campo(
    client: Client, campo: str, valor: str, mensaje: str
) -> None:
    datos = {"nombre": "JMP", "color_primario": "#0d2440", "color_acento": "#f2cf3a"}
    datos[campo] = valor
    respuesta = entrar(client, ORGANIZACION).post(URL, datos)
    assert respuesta.status_code == 200
    assert mensaje in " ".join(respuesta.context["form"].errors[campo])
    assert Organizador.actual().color_primario == "#0d2440"


@pytest.mark.django_db
def test_la_mesa_no_cambia_los_datos_de_la_escuela(client: Client) -> None:
    respuesta = entrar(client, MESA).get(URL)
    assert respuesta.status_code == 403
    assert "Solo la organización puede cambiar los datos de la escuela" in (
        respuesta.content.decode()
    )
