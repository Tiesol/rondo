"""T5.1: bloqueos de la ACF (PRO-07). Datos inventados."""

from datetime import datetime, timedelta
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import IntegrityError, transaction
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import Bloqueo, CategoriaNivel, Club, Equipo, Partido, Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo


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
    return torneo


def entrar(client: Client, grupo: str) -> Client:
    usuario = User.objects.create_user(grupo[:4], password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


def primer_dia(torneo: Torneo) -> tuple[datetime, datetime]:
    franja = torneo.franjas.order_by("inicio").first()
    assert franja is not None
    return franja.inicio, franja.fin


@pytest.mark.django_db
def test_programar_respeta_el_bloqueo(torneo: Torneo) -> None:
    equipo = Equipo.objects.get(nombre="Equipo 0")
    inicio, fin = primer_dia(torneo)
    bloqueo = Bloqueo.objects.create(torneo=torneo, inicio=inicio, fin=fin)
    bloqueo.equipos.add(equipo)
    corrida = programar_torneo(torneo)
    assert corrida.resultado["choques"] == {}
    for partido in Partido.objects.filter(local=equipo) | Partido.objects.filter(visitante=equipo):
        assert partido.inicio is not None
        assert not (inicio <= partido.inicio < fin)


@pytest.mark.django_db
def test_el_fin_va_despues_del_inicio(torneo: Torneo) -> None:
    ahora = timezone.now()
    with pytest.raises(IntegrityError), transaction.atomic():
        Bloqueo.objects.create(torneo=torneo, inicio=ahora, fin=ahora - timedelta(hours=1))


@pytest.mark.django_db
def test_la_pantalla_muestra_los_partidos_que_chocan(client: Client, torneo: Torneo) -> None:
    programar_torneo(torneo)
    partido = (
        Partido.objects.filter(inicio__isnull=False, local__isnull=False)
        .select_related("local")
        .first()
    )
    assert partido is not None and partido.inicio is not None and partido.local is not None
    local = timezone.localtime(partido.inicio)
    datos = {
        "equipos": [partido.local.pk],
        "dia": local.date().isoformat(),
        "desde": (local - timedelta(minutes=30)).strftime("%H:%M"),
        "hasta": (local + timedelta(minutes=30)).strftime("%H:%M"),
        "motivo": "Partido de la ACF",
    }
    org = entrar(client, ORGANIZACION)
    vivo = org.post(f"/torneos/{torneo.pk}/acf/revisar/", datos).content.decode()
    assert "<html" not in vivo
    assert local.strftime("%H:%M") in vivo
    assert partido.local.nombre in vivo
    respuesta = org.post(f"/torneos/{torneo.pk}/acf/", datos)
    assert respuesta.status_code == 302
    bloqueo = Bloqueo.objects.get()
    assert list(bloqueo.equipos.all()) == [partido.local]
    assert "1 partido choca" in org.get(f"/torneos/{torneo.pk}/acf/").content.decode()


@pytest.mark.django_db
def test_un_horario_al_reves_muestra_el_error(client: Client, torneo: Torneo) -> None:
    datos = {
        "equipos": [Equipo.objects.first().pk],  # type: ignore[union-attr]
        "dia": "2026-10-24",
        "desde": "12:00",
        "hasta": "10:00",
        "motivo": "ACF",
    }
    respuesta = entrar(client, ORGANIZACION).post(f"/torneos/{torneo.pk}/acf/", datos)
    assert respuesta.status_code == 200
    assert respuesta.context["form"].errors["hasta"]
    assert not Bloqueo.objects.exists()


@pytest.mark.django_db
def test_se_borra_un_bloqueo(client: Client, torneo: Torneo) -> None:
    inicio, fin = primer_dia(torneo)
    bloqueo = Bloqueo.objects.create(torneo=torneo, inicio=inicio, fin=fin)
    entrar(client, ORGANIZACION).post(f"/bloqueos/{bloqueo.pk}/borrar/")
    assert not Bloqueo.objects.exists()


@pytest.mark.django_db
def test_la_mesa_no_carga_bloqueos(client: Client, torneo: Torneo) -> None:
    respuesta = entrar(client, MESA).get(f"/torneos/{torneo.pk}/acf/")
    assert respuesta.status_code == 403
    assert "Solo la organización puede cargar partidos de la ACF" in respuesta.content.decode()
