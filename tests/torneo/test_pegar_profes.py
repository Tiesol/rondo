"""T7.9: pegar el cuerpo técnico, con el rol escrito de cualquier forma. Datos inventados."""

from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Profe, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion

PROFES = (
    "Nº\tNOMBRES\tAPELLIDOS\tFECHA DE NACIMIENTO\tNº DOCUMENTO\tFUNCION\tNº TELEFONO\n"
    "1\tCarlos\tSuárez Inventado\t01/01/1990\t5000001\tD.T\t70000000\n"
    "2\tMario\tVaca Inventado\t02/02/1991\t5000002\tAsistente\t70000001\n"
    "3\tRosa\tPaz Inventada\t03/03/1992\t5000003\tDelegado\t70000002\n"
)


@pytest.fixture
def river9() -> Equipo:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    club = Club.objects.create(nombre="River Plate")
    return Equipo.objects.create(club=club, categoria=cn, nombre="River Plate")


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


def url(equipo: Equipo) -> str:
    return f"/equipos/{equipo.pk}/profes/pegar/"


def revisar(cliente: Client, equipo: Equipo, texto: str) -> Any:
    paso1 = cliente.post(url(equipo), {"paso": "columnas", "texto": texto})
    columnas = {f"col{i}": c for i, c in enumerate(paso1.context["analisis"].columnas)}
    return paso1, cliente.post(url(equipo), {"paso": "revisar", "texto": texto} | columnas)


def guardar(cliente: Client, equipo: Equipo, vista: Any) -> Any:
    filas = vista.context["filas"]
    datos: dict[str, str] = {"paso": "guardar", "n": str(len(filas))}
    for i, fila in enumerate(filas):
        datos[f"f{i}-numero"] = str(fila.numero)
        datos |= {f"f{i}-{campo}": valor for campo, valor in fila.campos.items()}
    return cliente.post(url(equipo), datos)


@pytest.mark.django_db
def test_la_ficha_ofrece_pegar_el_cuerpo_tecnico(org: Client, river9: Equipo) -> None:
    assert url(river9) in org.get(f"/equipos/{river9.pk}/cuerpo-tecnico/").content.decode()


@pytest.mark.django_db
def test_pegar_dt_asistente_y_delegado_carga_los_tres_roles(org: Client, river9: Equipo) -> None:
    paso1, vista = revisar(org, river9, PROFES)
    # La fecha de nacimiento no se pide a los profes: esa columna se propone ignorar.
    assert paso1.context["analisis"].columnas == [
        "ignorar", "nombres", "apellidos", "ignorar", "documento", "rol", "ignorar",
    ]  # fmt: skip
    respuesta = guardar(org, river9, vista)
    assert respuesta["Location"] == f"/equipos/{river9.pk}/cuerpo-tecnico/"
    roles = sorted(Profe.objects.filter(equipo=river9).values_list("rol", flat=True))
    assert roles == ["asistente", "delegado", "entrenador"]


@pytest.mark.django_db
def test_un_segundo_entrenador_o_un_cuarto_profe_es_error(org: Client, river9: Equipo) -> None:
    texto = PROFES + "4\tLuis\tRoca Inventado\t\t5000004\tDT\t\n"
    _, vista = revisar(org, river9, texto)
    cuarto = vista.context["filas"][3]
    assert any(h.regla == "INS-08" for h in cuarto.errores)
    guardar(org, river9, vista)
    assert Profe.objects.filter(equipo=river9).count() == 3


@pytest.mark.django_db
def test_un_rol_que_no_se_reconoce_queda_para_corregir(org: Client, river9: Equipo) -> None:
    texto = "Carlos\tSuárez Inventado\tUtilero\n"
    _, vista = revisar(org, river9, texto)
    fila = vista.context["filas"][0]
    assert fila.errores and "Utilero" in fila.errores[0].mensaje
    assert fila.campos["rol"] == "Utilero"
