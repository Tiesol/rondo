"""T13.21: "Fijar este partido". Un partido fijado no lo mueve nada automático: ni programar,
ni rehacer el fixture, ni las propuestas. Se mueve solo a mano, y "Desfijar" lo libera. Mover
no fija solo. Datos inventados."""

from datetime import timedelta
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import Bloqueo, CategoriaNivel, Club, Equipo, Partido, Registro, Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo
from torneo.servicios.reprogramar import calcular_propuestas, mover_a_mano


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    for categoria in ("Sub 9", "Sub 10"):
        cn: CategoriaNivel = torneo.categorias.get(categoria=categoria, nivel="inicial")
        for i in range(4):
            club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
            Equipo.objects.create(club=club, categoria=cn, nombre=f"{categoria} {i}")
        generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    return torneo


def entrar(client: Client, rol: str) -> Client:
    usuario = User.objects.create_user(rol[:4], password="x")
    usuario.groups.add(Group.objects.get(name=rol))
    client.force_login(usuario)
    return client


def un_partido() -> Partido:
    partido = (
        Partido.objects.filter(inicio__isnull=False, fase="grupos")
        .select_related("categoria__torneo", "cancha", "local", "visitante")
        .order_by("inicio")
        .first()
    )
    assert partido is not None
    return partido


def a_otro_lugar(partido: Partido) -> None:
    """Un lugar libre, el más lejano de los sugeridos: el programador no lo elegiría."""
    from torneo.servicios.sugerencias import horarios_libres

    assert partido.inicio is not None
    libres, _ = horarios_libres(partido, cuantos=40, ahora=partido.inicio - timedelta(days=1))
    destino = libres[-1]
    mover_a_mano(partido, destino.cancha, destino.inicio)
    partido.refresh_from_db()


@pytest.mark.django_db
def test_mover_no_fija_solo(torneo: Torneo) -> None:
    partido = un_partido()
    a_otro_lugar(partido)
    assert partido.fijado is False


@pytest.mark.django_db
def test_fijar_y_desfijar_desde_la_ficha_con_historial(client: Client, torneo: Torneo) -> None:
    partido = un_partido()
    org = entrar(client, ORGANIZACION)
    ficha = org.get(f"/partidos/{partido.pk}/ficha/").content.decode()
    assert f"/partidos/{partido.pk}/fijar/" in ficha and "Fijar este partido" in ficha
    org.post(f"/partidos/{partido.pk}/fijar/")
    partido.refresh_from_db()
    assert partido.fijado
    assert "Desfijar" in org.get(f"/partidos/{partido.pk}/ficha/").content.decode()
    dia = timezone.localtime(partido.inicio).date().isoformat()
    assert "Fijado" in org.get(f"/calendario/{dia}/").content.decode()
    org.post(f"/partidos/{partido.pk}/fijar/")
    partido.refresh_from_db()
    assert not partido.fijado
    assert set(Registro.objects.filter(partido=partido).values_list("que", flat=True)) >= {
        "Fijado",
        "Desfijado",
    }


@pytest.mark.django_db
def test_la_mesa_no_fija(client: Client, torneo: Torneo) -> None:
    partido = un_partido()
    assert entrar(client, MESA).post(f"/partidos/{partido.pk}/fijar/").status_code == 403


@pytest.mark.django_db
def test_mover_puede_fijar_a_la_vez(client: Client, torneo: Torneo) -> None:
    partido = un_partido()
    assert partido.cancha is not None and partido.inicio is not None
    local = timezone.localtime(partido.inicio)
    entrar(client, ORGANIZACION).post(
        f"/partidos/{partido.pk}/mover/",
        {
            "dia": local.date().isoformat(),
            "hora": local.strftime("%H:%M"),
            "cancha": partido.cancha.codigo,
            "fijar": "on",
        },
    )
    partido.refresh_from_db()
    assert partido.fijado


@pytest.mark.django_db
def test_volver_a_programar_no_mueve_un_fijado(torneo: Torneo) -> None:
    partido = un_partido()
    a_otro_lugar(partido)
    Partido.objects.filter(pk=partido.pk).update(fijado=True)
    lugar = (partido.cancha_id, partido.inicio)
    programar_torneo(torneo)
    partido.refresh_from_db()
    assert (partido.cancha_id, partido.inicio) == lugar


@pytest.mark.django_db
def test_las_propuestas_no_mueven_un_fijado(torneo: Torneo) -> None:
    partido = un_partido()
    Partido.objects.filter(pk=partido.pk).update(fijado=True)
    assert partido.inicio is not None and partido.local is not None
    bloqueo = Bloqueo.objects.create(
        torneo=torneo,
        inicio=partido.inicio,
        fin=partido.inicio + timedelta(minutes=30),
        motivo="Partido de la ACF",
    )
    bloqueo.equipos.set([partido.local])
    corrida = calcular_propuestas(bloqueo)
    movidos = {m["partido"] for p in corrida.resultado["propuestas"] for m in p}
    assert partido.pk not in movidos


@pytest.mark.django_db
def test_rehacer_el_fixture_conserva_el_lugar_del_fijado(torneo: Torneo) -> None:
    partido = un_partido()
    Partido.objects.filter(pk=partido.pk).update(fijado=True)
    par = {partido.local_id, partido.visitante_id}
    lugar = (partido.cancha_id, partido.inicio)
    generar_fixture(partido.categoria, semilla=1)  # mismos equipos: el cruce sigue existiendo
    nuevo = next(
        p
        for p in Partido.objects.filter(categoria=partido.categoria, fase="grupos")
        if {p.local_id, p.visitante_id} == par
    )
    assert nuevo.fijado and (nuevo.cancha_id, nuevo.inicio) == lugar
