"""T8.9: suspensiones en la ficha del partido. Datos inventados."""

from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Jugador, Partido, Persona, Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios import partido as servicio
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.suspensiones import suspendidos_en


def categoria_con(categoria: str, nivel: str = "avanzado") -> CategoriaNivel:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria=categoria, nivel=nivel)
    for i in range(4):
        club = Club.objects.create(nombre=f"{categoria} Club {i}")
        equipo = Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}")
        persona = Persona.objects.create(nombres=f"Nombre{i}", apellidos="Inventado")
        Jugador.objects.create(persona=persona, equipo=equipo, dorsal=10)
    generar_fixture(cn, semilla=1)
    return cn


def primero_y_siguiente(cn: CategoriaNivel) -> tuple[Partido, Partido, Jugador]:
    primero = cn.partidos.filter(fase="grupos").order_by("fecha", "pk").first()
    assert primero is not None and primero.local is not None
    siguiente = (
        cn.partidos.filter(fase="grupos", fecha__gt=primero.fecha)
        .filter(local=primero.local)
        .union(cn.partidos.filter(fase="grupos", fecha__gt=primero.fecha, visitante=primero.local))
        .order_by("fecha", "pk")
        .first()
    )
    assert siguiente is not None
    jugador = primero.local.jugadores.first()
    assert jugador is not None
    return primero, siguiente, jugador


def doble_amarilla(partido: Partido, jugador: Jugador) -> None:
    servicio.empezar(partido, None)
    servicio.anotar(partido, "amarilla", jugador.equipo, jugador, None)
    servicio.anotar(partido, "amarilla", jugador.equipo, jugador, None)
    servicio.terminar(partido, None)


def entrar(client: Client, grupo: str) -> Client:
    usuario = User.objects.create_user(grupo[:4], password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


@pytest.mark.django_db
def test_doble_amarilla_en_sub_12_sin_pagar_suspende_el_proximo(client: Client) -> None:
    cn = categoria_con("Sub 12")
    primero, siguiente, jugador = primero_y_siguiente(cn)
    doble_amarilla(primero, jugador)
    assert [(j, m) for j, m in suspendidos_en(siguiente)] == [
        (jugador, "Doble amarilla sin pagar la multa")
    ]
    mesa = entrar(client, MESA)
    html = mesa.get(f"/partidos/{siguiente.pk}/ficha/").content.decode()
    assert "Suspendido" in html and "Nombre0" in html
    # La mesa marca que pagó la multa (Bs 30) en la ficha del partido donde fue.
    ficha = mesa.get(f"/partidos/{primero.pk}/ficha/").content.decode()
    assert "Bs 30" in ficha
    mesa.post(
        f"/partidos/{primero.pk}/ficha/accion/",
        {"accion": "multa", "jugador": jugador.pk, "pagada": "on"},
    )
    assert suspendidos_en(siguiente) == []


@pytest.mark.django_db
def test_doble_amarilla_en_sub_8_no_suspende() -> None:
    cn = categoria_con("Sub 8")
    primero, siguiente, jugador = primero_y_siguiente(cn)
    doble_amarilla(primero, jugador)
    assert suspendidos_en(siguiente) == []


@pytest.mark.django_db
def test_la_organizacion_marca_una_suspension_a_mano(client: Client) -> None:
    cn = categoria_con("Sub 12")
    primero, siguiente, jugador = primero_y_siguiente(cn)
    servicio.empezar(primero, None)
    servicio.anotar(primero, "roja", jugador.equipo, jugador, None)
    servicio.terminar(primero, None)
    assert suspendidos_en(siguiente) == []  # P29: la roja directa no suspende sola
    org = entrar(client, ORGANIZACION)
    org.post(
        f"/partidos/{primero.pk}/ficha/accion/",
        {"accion": "suspender", "jugador": jugador.pk, "partidos": "1", "motivo": "Roja directa"},
    )
    assert [m for _, m in suspendidos_en(siguiente)] == ["Roja directa"]
    html = org.get(f"/partidos/{siguiente.pk}/ficha/").content.decode()
    assert "Suspendido" in html


@pytest.mark.django_db
def test_la_mesa_no_suspende_a_mano(client: Client, settings: Any) -> None:
    cn = categoria_con("Sub 12")
    primero, _, jugador = primero_y_siguiente(cn)
    mesa = entrar(client, MESA)
    respuesta = mesa.post(
        f"/partidos/{primero.pk}/ficha/accion/",
        {"accion": "suspender", "jugador": jugador.pk, "partidos": "1", "motivo": "x"},
        follow=True,
    )
    assert "Solo la organización" in respuesta.content.decode()
