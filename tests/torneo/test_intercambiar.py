"""B5 (fase 12): intercambiar dos partidos en un solo paso. Datos inventados."""

from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Cambio, CategoriaNivel, Club, Equipo, Partido, Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo, verificar_torneo
from torneo.servicios.reprogramar import (
    ChoqueAlMover,
    candidatos_de_intercambio,
    intercambiar,
    veces_que_reprogramo,
)


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10
    settings.PROGRAMADOR_TRABAJADORES = 4


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    for categoria, nivel in (("Sub 9", "avanzado"), ("Sub 9", "inicial"), ("Sub 8", "avanzado")):
        cn: CategoriaNivel = torneo.categorias.get(categoria=categoria, nivel=nivel)
        for i in range(4):
            club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
            Equipo.objects.create(club=club, categoria=cn, nombre=f"{categoria[-1]}{nivel[:3]}{i}")
        generar_fixture(cn, semilla=2)
    programar_torneo(torneo)
    return torneo


def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


def un_partido() -> Partido:
    p = (
        Partido.objects.filter(inicio__isnull=False, categoria__categoria="Sub 9")
        .select_related("cancha", "categoria")
        .order_by("inicio")
        .first()
    )
    assert p is not None
    return p


@pytest.mark.django_db
def test_los_candidatos_son_de_canchas_compatibles_y_los_sin_choques_van_primero(
    torneo: Torneo,
) -> None:
    partido = un_partido()
    candidatos = candidatos_de_intercambio(partido)
    assert candidatos
    propias = {c.codigo for c in partido.categoria.canchas.all()}
    for c in candidatos:
        assert c.partido.cancha is not None and c.partido.cancha.codigo in propias
    orden = [(c.bloquea, len(c.avisos)) for c in candidatos]
    assert orden == sorted(orden)


@pytest.mark.django_db
def test_intercambiar_deja_los_dos_donde_estaba_el_otro_con_historial(torneo: Torneo) -> None:
    partido = un_partido()
    limpio = next(c for c in candidatos_de_intercambio(partido) if c.sin_choques)
    otro = limpio.partido
    lugar_a, lugar_b = (partido.cancha_id, partido.inicio), (otro.cancha_id, otro.inicio)
    pidio = partido.local
    assert pidio is not None
    intercambiar(partido, otro, None, pidio=pidio)
    partido.refresh_from_db()
    otro.refresh_from_db()
    assert (partido.cancha_id, partido.inicio) == lugar_b
    assert (otro.cancha_id, otro.inicio) == lugar_a
    assert Cambio.objects.filter(partido__in=[partido, otro]).count() == 2
    assert veces_que_reprogramo(pidio) == 1  # cuenta para el equipo que lo pidió
    assert veces_que_reprogramo(otro.local) == 0  # type: ignore[arg-type]
    assert verificar_torneo(torneo) == {}


@pytest.mark.django_db
def test_un_aviso_se_confirma_y_lo_imposible_no_se_guarda(torneo: Torneo) -> None:
    partido = un_partido()
    con_avisos = [c for c in candidatos_de_intercambio(partido) if c.avisos and not c.bloquea]
    if con_avisos:
        otro = con_avisos[0].partido
        lugar = (partido.cancha_id, partido.inicio)
        with pytest.raises(ChoqueAlMover) as error:
            intercambiar(partido, otro, None)
        assert not error.value.bloquea
        partido.refresh_from_db()
        assert (partido.cancha_id, partido.inicio) == lugar  # no se movió
        intercambiar(partido, otro, None, confirmar=True)
    # Un partido que ya empezó no se mueve nunca.
    otro = candidatos_de_intercambio(un_partido())[0].partido
    Partido.objects.filter(pk=otro.pk).update(estado="en_juego")
    with pytest.raises(ChoqueAlMover) as error:
        intercambiar(un_partido(), otro, None, confirmar=True)
    assert error.value.bloquea


@pytest.mark.django_db
def test_desde_la_pantalla(client: Client, torneo: Torneo) -> None:
    cliente = org(client)
    partido = un_partido()
    assert (
        f"/partidos/{partido.pk}/intercambiar/"
        in cliente.get(f"/partidos/{partido.pk}/mover/").content.decode()
    )
    html = cliente.get(f"/partidos/{partido.pk}/intercambiar/").content.decode()
    assert "Intercambiar con" in html and "¿Quién pidió el cambio?" in html
    limpio = next(c for c in candidatos_de_intercambio(partido) if c.sin_choques)
    respuesta = cliente.post(
        f"/partidos/{partido.pk}/intercambiar/",
        {"otro": limpio.partido.pk, "pidio": partido.local_id},
    )
    assert respuesta.status_code == 302
    assert veces_que_reprogramo(partido.local) == 1  # type: ignore[arg-type]


@pytest.mark.django_db
def test_la_mesa_no_intercambia(client: Client, torneo: Torneo) -> None:
    usuario = User.objects.create_user("mesa", password="x")
    usuario.groups.add(Group.objects.get(name=MESA))
    client.force_login(usuario)
    assert client.get(f"/partidos/{un_partido().pk}/intercambiar/").status_code == 403
