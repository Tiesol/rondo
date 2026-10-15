"""T13.23: lo editado a mano se respeta. Rehacer el fixture conserva la fecha de los cruces
editados que siguen existiendo; programar no cambia quién juega con quién. Después de editar, la
organización elige "Reprogramar lo cambiado" o "Dejarlo así". Datos inventados."""

from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Corrida, Equipo, Partido, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.cruces_a_mano import rearmar_fecha
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10


@pytest.fixture
def cn() -> CategoriaNivel:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="inicial")
    for letra in "ABCD":
        Equipo.objects.create(club=Club.objects.create(nombre=letra), categoria=cn, nombre=letra)
    generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    return cn


def equipo(letra: str) -> Equipo:
    return Equipo.objects.get(nombre=letra)


def fecha_del_cruce(cn: CategoriaNivel, a: str, b: str) -> int:
    pks = {equipo(a).pk, equipo(b).pk}
    return next(
        p.fecha for p in cn.partidos.filter(fase="grupos") if {p.local_id, p.visitante_id} == pks
    )  # type: ignore[return-value]


def adelantar_a_d(cn: CategoriaNivel) -> int:
    """Rearma la fecha de A-B para que juegue A-D y B-C; devuelve esa fecha."""
    uno = fecha_del_cruce(cn, "A", "B")
    partidos = list(cn.partidos.filter(fase="grupos", fecha=uno).order_by("pk"))
    otra = fecha_del_cruce(cn, "A", "D")
    de_otra = list(cn.partidos.filter(fase="grupos", fecha=otra).order_by("pk"))
    rearmar_fecha(
        cn,
        uno,
        {partidos[0].pk: (equipo("A"), equipo("D")), partidos[1].pk: (equipo("B"), equipo("C"))},
        None,
    )
    rearmar_fecha(
        cn,
        otra,
        {de_otra[0].pk: (equipo("A"), equipo("B")), de_otra[1].pk: (equipo("C"), equipo("D"))},
        None,
    )
    return uno


@pytest.mark.django_db
def test_rehacer_el_fixture_conserva_la_fecha_de_lo_editado(cn: CategoriaNivel) -> None:
    uno = adelantar_a_d(cn)
    perdidos = generar_fixture(cn, semilla=7)
    assert perdidos == []
    assert fecha_del_cruce(cn, "A", "D") == uno
    assert fecha_del_cruce(cn, "B", "C") == uno
    assert cn.partidos.filter(editado_a_mano=True).exists()


@pytest.mark.django_db
def test_programar_no_cambia_los_cruces_editados(cn: CategoriaNivel) -> None:
    uno = adelantar_a_d(cn)
    programar_torneo(cn.torneo)
    assert fecha_del_cruce(cn, "A", "D") == uno


@pytest.mark.django_db
def test_despues_de_editar_reprogramar_lo_cambiado_o_dejarlo(
    client: Client, cn: CategoriaNivel
) -> None:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    uno = fecha_del_cruce(cn, "A", "B")
    partidos = list(cn.partidos.filter(fase="grupos", fecha=uno).order_by("pk"))
    datos: dict[str, str] = {"accion": "rearmar"}
    for p in partidos:
        datos |= {f"local_{p.pk}": str(p.visitante_id), f"visitante_{p.pk}": str(p.local_id)}
    respuesta = client.post(f"/torneo/{cn.pk}/fecha/{uno}/", datos)
    assert respuesta["Location"] == f"/torneo/{cn.pk}/fecha/{uno}/?editada=1"
    html = client.get(respuesta["Location"]).content.decode()
    assert "Reprogramar lo cambiado" in html and "Dejarlo así" in html
    otros = {
        p.pk: (p.cancha_id, p.inicio) for p in cn.partidos.exclude(fecha=uno).filter(fase="grupos")
    }
    client.post(f"/torneo/{cn.pk}/fecha/{uno}/", {"accion": "reprogramar"})
    assert Corrida.objects.filter(tipo=Corrida.Tipo.PROGRAMAR).count() == 2
    for p in cn.partidos.filter(fecha=uno):
        assert p.estado == Partido.Estado.PROGRAMADO and p.inicio is not None
    for p in cn.partidos.exclude(fecha=uno).filter(fase="grupos"):
        assert (p.cancha_id, p.inicio) == otros[p.pk], "lo demás no se mueve"
