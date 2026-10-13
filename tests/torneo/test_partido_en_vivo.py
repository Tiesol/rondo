"""T10.9: el partido en vivo, a mano: tiempos, amonestación verbal y "sale 5 minutos"."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Jugador, Partido, Persona, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios import partido as servicio
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture


def partido_de(categoria: str, nivel: str = "avanzado") -> Partido:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria=categoria, nivel=nivel)
    for i in range(4):
        equipo = Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
        persona = Persona.objects.create(nombres=f"Nombre{i}", apellidos="Inventado")
        Jugador.objects.create(persona=persona, equipo=equipo, dorsal=7)
    generar_fixture(cn, semilla=1)
    p = cn.partidos.filter(fase="grupos").first()
    assert p is not None
    return p


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


def hacer(cliente: Client, partido: Partido, **datos: object) -> None:
    cliente.post(f"/partidos/{partido.pk}/ficha/accion/", datos)


@pytest.mark.django_db
def test_la_mesa_marca_los_tiempos_del_partido(org: Client) -> None:
    partido = partido_de("Sub 9")
    hacer(org, partido, accion="empezar")
    partido.refresh_from_db()
    assert partido.tiempo == "primer_tiempo" and partido.inicio_real is not None
    assert "1.er tiempo" in org.get(f"/partidos/{partido.pk}/ficha/").content.decode()
    hacer(org, partido, accion="avanzar_tiempo")
    partido.refresh_from_db()
    assert partido.tiempo == "descanso" and partido.fin_primer_tiempo is not None
    hacer(org, partido, accion="avanzar_tiempo")
    partido.refresh_from_db()
    assert partido.tiempo == "segundo_tiempo" and partido.fin_descanso is not None
    hacer(org, partido, accion="terminar")
    partido.refresh_from_db()
    assert partido.tiempo == "terminado" and partido.fin_real is not None


@pytest.mark.django_db
def test_amonestacion_verbal(org: Client) -> None:
    partido = partido_de("Sub 7")
    assert partido.local is not None
    jugador = partido.local.jugadores.first()
    assert jugador is not None
    hacer(org, partido, accion="empezar")
    hacer(org, partido, evento=f"amonestacion|{partido.local_id}|{jugador.pk}")
    html = org.get(f"/partidos/{partido.pk}/ficha/").content.decode()
    assert "Amonestación" in html
    assert servicio.resultado_de(partido).marcador == (0, 0)


@pytest.mark.django_db
def test_doble_amarilla_hasta_sub_9_sale_cinco_minutos(org: Client) -> None:
    partido = partido_de("Sub 9")
    assert partido.local is not None
    jugador = partido.local.jugadores.first()
    hacer(org, partido, accion="empezar")
    for _ in range(2):
        hacer(org, partido, evento=f"amarilla|{partido.local_id}|{jugador.pk}")  # type: ignore[union-attr]
    html = org.get(f"/partidos/{partido.pk}/ficha/").content.decode()
    assert "Afuera 5 min" in html


@pytest.mark.django_db
def test_sin_mejor_jugador_si_el_torneo_lo_apaga(org: Client) -> None:
    partido = partido_de("Sub 9")
    torneo = partido.categoria.torneo
    hacer(org, partido, accion="empezar")
    assert "Mejor jugador" in org.get(f"/partidos/{partido.pk}/ficha/").content.decode()
    torneo.reglas = torneo.reglas | {"mejor_jugador": False}
    torneo.save()
    assert "Mejor jugador" not in org.get(f"/partidos/{partido.pk}/ficha/").content.decode()
