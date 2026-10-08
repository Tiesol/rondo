"""T5.5: suspender un día y agregar un día entre semana. Datos inventados."""

from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Corrida, Equipo, Franja, Partido, Torneo
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


def dia_con_partidos() -> str:
    primero = Partido.objects.filter(inicio__isnull=False, fase="grupos").order_by("inicio").first()
    assert primero is not None and primero.inicio is not None
    return timezone.localtime(primero.inicio).date().isoformat()


@pytest.mark.django_db
def test_suspender_deja_pendientes_y_las_propuestas_los_ubican_en_otro_dia(
    client: Client, torneo: Torneo
) -> None:
    dia = dia_con_partidos()
    del_dia = [
        p.pk
        for p in Partido.objects.filter(inicio__isnull=False)
        if timezone.localtime(p.inicio).date().isoformat() == dia
    ]
    org = entrar(client, ORGANIZACION)
    respuesta = org.post(f"/calendario/{dia}/suspender/")
    assert set(Partido.objects.filter(pk__in=del_dia).values_list("estado", flat=True)) == {
        "pendiente"
    }
    assert all(
        f.suspendida
        for f in torneo.franjas.all()
        if timezone.localtime(f.inicio).date().isoformat() == dia
    )
    corrida = Corrida.objects.get(tipo=Corrida.Tipo.REPROGRAMAR)
    assert respuesta["Location"] == f"/corridas/{corrida.pk}/propuestas/"
    assert corrida.resultado["propuestas"], "hay que poder ubicarlos en otro día"
    org.post(f"/corridas/{corrida.pk}/aplicar/0/")
    assert verificar_torneo(torneo) == {}
    for partido in Partido.objects.filter(pk__in=del_dia):
        assert partido.inicio is not None
        assert timezone.localtime(partido.inicio).date().isoformat() != dia


@pytest.mark.django_db
def test_programar_no_usa_un_dia_suspendido(torneo: Torneo) -> None:
    dia = dia_con_partidos()
    for franja in torneo.franjas.all():
        if timezone.localtime(franja.inicio).date().isoformat() == dia:
            franja.suspendida = True
            franja.save()
    programar_torneo(torneo)
    assert not any(
        timezone.localtime(p.inicio).date().isoformat() == dia
        for p in Partido.objects.filter(inicio__isnull=False)
        if p.inicio
    )


@pytest.mark.django_db
def test_agregar_un_dia_entre_semana(client: Client, torneo: Torneo) -> None:
    org = entrar(client, ORGANIZACION)
    respuesta = org.post(
        "/calendario/agregar-dia/", {"dia": "2026-10-28", "desde": "17:00", "hasta": "20:00"}
    )
    assert respuesta["Location"] == "/calendario/2026-10-28/"
    franja = Franja.objects.get(tipo=Franja.Tipo.ENTRE_SEMANA)
    assert timezone.localtime(franja.inicio).hour == 17
    html = org.get("/calendario/2026-10-28/").content.decode()
    assert "Mié" in html


@pytest.mark.django_db
def test_la_mesa_no_suspende_ni_agrega_dias(client: Client, torneo: Torneo) -> None:
    mesa = entrar(client, MESA)
    assert mesa.post(f"/calendario/{dia_con_partidos()}/suspender/").status_code == 403
    assert mesa.post("/calendario/agregar-dia/", {}).status_code == 403
