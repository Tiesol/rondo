"""TU.3: las reglas del torneo se editan con interruptores, números y listas, sin JSON."""

from datetime import date
from typing import Any

import pytest
from django.contrib.auth.models import Group, User
from django.test import Client
from pydantic import Field

from dominio.config import Reglas
from torneo.forms.reglas import FormularioReglas
from torneo.models import Torneo
from torneo.permisos import MESA, ORGANIZACION


@pytest.fixture
def torneo() -> Torneo:
    return Torneo.objects.create(
        nombre="JMP CUP", edicion=5, anio=2026, inicio=date(2026, 10, 23), fin=date(2026, 11, 22)
    )


def entrar(client: Client, grupo: str) -> Client:
    usuario = User.objects.create_user(grupo[:4], password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


def datos_validos(**cambios: Any) -> dict[str, Any]:
    datos: dict[str, Any] = {}
    for nombre, valor in Reglas().model_dump(mode="json").items():
        if isinstance(valor, bool):
            if valor:
                datos[nombre] = "on"
        elif isinstance(valor, list):
            datos[f"{nombre}_0"], datos[f"{nombre}_1"] = valor
        elif valor is not None:
            datos[nombre] = valor
    datos.update(cambios)
    return datos


@pytest.mark.django_db
def test_se_ven_todas_las_reglas_con_su_pregunta_y_sin_json(client: Client, torneo: Torneo) -> None:
    html = entrar(client, ORGANIZACION).get(f"/torneos/{torneo.pk}/reglas/").content.decode()
    assert "Se puede jugar en una categoría mayor" in html
    assert "P6" in html
    assert 'role="switch"' in html
    assert "<textarea" not in html
    assert "&quot;jugar_en_categoria_mayor&quot;" not in html


@pytest.mark.django_db
def test_guardar_cambia_las_reglas(client: Client, torneo: Torneo) -> None:
    datos = datos_validos(max_partidos_por_dia=3, marcador_wo_0=2)
    del datos["jugador_y_profe"]  # interruptor apagado
    respuesta = entrar(client, ORGANIZACION).post(f"/torneos/{torneo.pk}/reglas/", datos)
    assert respuesta.status_code == 302
    torneo.refresh_from_db()
    assert torneo.reglas["max_partidos_por_dia"] == 3
    assert torneo.reglas["jugador_y_profe"] is False
    assert torneo.reglas["marcador_wo"] == [2, 0]


@pytest.mark.django_db
def test_un_valor_invalido_muestra_el_error_y_no_guarda_nada(
    client: Client, torneo: Torneo
) -> None:
    antes = dict(torneo.reglas)
    datos = datos_validos(aviso_anios_menor=-1, max_partidos_por_dia=4)
    respuesta = entrar(client, ORGANIZACION).post(f"/torneos/{torneo.pk}/reglas/", datos)
    assert respuesta.status_code == 200
    assert respuesta.context["form"].errors["aviso_anios_menor"]
    torneo.refresh_from_db()
    assert torneo.reglas == antes


@pytest.mark.django_db
def test_la_mesa_no_cambia_las_reglas(client: Client, torneo: Torneo) -> None:
    respuesta = entrar(client, MESA).get(f"/torneos/{torneo.pk}/reglas/")
    assert respuesta.status_code == 403
    assert "Solo la organización puede cambiar las reglas" in respuesta.content.decode()


def test_el_formulario_se_arma_con_las_reglas_nuevas() -> None:
    class ReglasConUnaMas(Reglas):
        dias_de_gracia: int = Field(
            default=2,
            ge=0,
            title="Días de gracia",
            description="Inventada para el test.",
            json_schema_extra={"grupo": "Inscripción", "pregunta": "P99"},
        )

    formulario = FormularioReglas(modelo=ReglasConUnaMas)
    assert formulario.fields["dias_de_gracia"].label == "Días de gracia"
