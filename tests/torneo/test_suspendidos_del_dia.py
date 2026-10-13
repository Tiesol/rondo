"""T9.2: la lista de suspendidos de cada día, para la mesa. Datos inventados."""

from datetime import datetime, timedelta
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Jugador, Partido, Persona, Torneo
from torneo.permisos import MESA
from torneo.servicios import partido as servicio
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture


@pytest.fixture
def escenario() -> tuple[Partido, Partido, Jugador]:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 12", nivel="avanzado")
    for i in range(4):
        equipo = Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
        persona = Persona.objects.create(nombres=f"Nombre{i}", apellidos="Inventado")
        Jugador.objects.create(persona=persona, equipo=equipo, dorsal=10)
    generar_fixture(cn, semilla=1)
    primero = cn.partidos.filter(fase="grupos").order_by("fecha", "pk").first()
    assert primero is not None and primero.local is not None
    siguiente = (
        cn.partidos.filter(fase="grupos", fecha__gt=primero.fecha, local=primero.local).first()
        or cn.partidos.filter(
            fase="grupos", fecha__gt=primero.fecha, visitante=primero.local
        ).first()
    )
    assert siguiente is not None
    sabado = timezone.make_aware(datetime(2026, 10, 24, 9, 0))
    Partido.objects.filter(pk=primero.pk).update(inicio=sabado)
    Partido.objects.filter(pk=siguiente.pk).update(inicio=sabado + timedelta(days=1))
    jugador = primero.local.jugadores.first()
    assert jugador is not None
    primero.refresh_from_db()
    servicio.empezar(primero, None)
    servicio.anotar(primero, "amarilla", jugador.equipo, jugador, None)
    servicio.anotar(primero, "amarilla", jugador.equipo, jugador, None)
    servicio.terminar(primero, None)
    return primero, siguiente, jugador


def mesa(client: Client) -> Client:
    usuario = User.objects.create_user("mesa", password="x")
    usuario.groups.add(Group.objects.get(name=MESA))
    client.force_login(usuario)
    return client


@pytest.mark.django_db
def test_el_suspendido_aparece_el_dia_de_su_proximo_partido(client: Client, escenario: Any) -> None:
    _, _, jugador = escenario
    cliente = mesa(client)
    domingo = cliente.get("/calendario/2026-10-25/suspendidos/").content.decode()
    assert "Nombre0 Inventado" in domingo or str(jugador.persona) in domingo
    assert "Doble amarilla" in domingo
    sabado = cliente.get("/calendario/2026-10-24/suspendidos/").content.decode()
    assert str(jugador.persona) not in sabado and "No hay suspendidos" in sabado


@pytest.mark.django_db
def test_el_calendario_del_dia_enlaza_la_lista(client: Client, escenario: Any) -> None:
    html = mesa(client).get("/calendario/2026-10-25/").content.decode()
    assert "/calendario/2026-10-25/suspendidos/" in html


@pytest.mark.django_db
def test_sin_rol_no_se_ve(client: Client, escenario: Any) -> None:
    client.force_login(User.objects.create_user("nadie", password="x"))
    assert client.get("/calendario/2026-10-25/suspendidos/").status_code == 403
