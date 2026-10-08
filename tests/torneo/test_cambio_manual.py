"""T5.4: mover un partido a mano, con el verificador antes de guardar. Datos inventados."""

from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import Cambio, CategoriaNivel, Club, Equipo, Partido, Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo, verificar_torneo


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10
    settings.PROGRAMADOR_TRABAJADORES = 4


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
        Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}")
    generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    return torneo


def entrar(client: Client, grupo: str) -> Client:
    usuario = User.objects.create_user(grupo[:4], password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


def programados() -> list[Partido]:
    return list(
        Partido.objects.filter(inicio__isnull=False, local__isnull=False)
        .select_related("cancha")
        .order_by("inicio")
    )


def datos(inicio: Any, cancha: str) -> dict[str, str]:
    local = timezone.localtime(inicio)
    return {"dia": local.date().isoformat(), "hora": local.strftime("%H:%M"), "cancha": cancha}


@pytest.mark.django_db
def test_mover_a_un_turno_libre_lo_guarda_fijado(client: Client, torneo: Torneo) -> None:
    partido = programados()[0]
    ocupados = {timezone.localtime(p.inicio).date() for p in programados() if p.inicio}
    libre = next(
        f
        for f in torneo.franjas.order_by("inicio")
        if timezone.localtime(f.inicio).date() not in ocupados
    )
    destino = libre.inicio  # un día sin partidos: no choca con nada
    respuesta = entrar(client, ORGANIZACION).post(
        f"/partidos/{partido.pk}/mover/", datos(destino, "C2")
    )
    assert respuesta.status_code == 302
    partido.refresh_from_db()
    assert partido.inicio == destino
    assert partido.fijado
    cambio = Cambio.objects.get()
    assert cambio.motivo == "Cambio a mano"
    assert verificar_torneo(torneo) == {}


@pytest.mark.django_db
def test_mover_encima_de_otro_muestra_el_choque_y_no_guarda(client: Client, torneo: Torneo) -> None:
    uno, otro = programados()[:2]
    assert otro.cancha is not None
    antes = (uno.cancha_id, uno.inicio)
    respuesta = entrar(client, ORGANIZACION).post(
        f"/partidos/{uno.pk}/mover/", datos(otro.inicio, otro.cancha.codigo)
    )
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert "No se guardó" in html
    assert "Se pisan en" in html or "a la vez" in html
    uno.refresh_from_db()
    assert (uno.cancha_id, uno.inicio) == antes
    assert not Cambio.objects.exists()


@pytest.mark.django_db
def test_la_mesa_no_mueve_partidos(client: Client, torneo: Torneo) -> None:
    partido = programados()[0]
    respuesta = entrar(client, MESA).get(f"/partidos/{partido.pk}/mover/")
    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_el_calendario_ofrece_mover_solo_a_la_organizacion(client: Client, torneo: Torneo) -> None:
    partido = programados()[0]
    dia = timezone.localtime(partido.inicio).date().isoformat()
    org = entrar(client, ORGANIZACION)
    assert f"/partidos/{partido.pk}/mover/" in org.get(f"/calendario/{dia}/").content.decode()
