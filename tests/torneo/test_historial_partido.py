"""T11.7: historial del partido. Quién cambió qué, cuándo y qué valía antes. Datos inventados."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Jugador, Partido, Persona, Registro, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios import partido as servicio
from torneo.servicios import planilla
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture


@pytest.fixture
def usuario() -> User:
    usuario = User.objects.create_user("ana", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    return usuario


@pytest.fixture
def partido() -> Partido:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"E{i}"
        )
    generar_fixture(cn, semilla=1)
    p = cn.partidos.filter(fase="grupos").select_related("local", "visitante").first()
    assert p is not None and p.local and p.visitante
    for equipo in (p.local, p.visitante):
        for i in range(2):
            Jugador.objects.create(
                persona=Persona.objects.create(nombres=f"N{i}", apellidos="Inventado"),
                equipo=equipo,
                dorsal=i + 1,
            )
    return p


def registros(partido: Partido) -> list[tuple[str, str, str]]:
    return [
        (r.que, r.antes, r.usuario.username if r.usuario else "")
        for r in Registro.objects.filter(partido=partido).order_by("fecha", "pk")
    ]


@pytest.mark.django_db
def test_cada_accion_queda_con_quien_y_lo_de_antes(partido: Partido, usuario: User) -> None:
    assert partido.local is not None
    jugador = partido.local.jugadores.get(dorsal=1)
    servicio.empezar(partido, usuario)
    servicio.anotar(partido, "gol", partido.local, jugador, usuario)
    servicio.deshacer(partido, usuario)
    planilla.cambiar_dorsal(partido, jugador, 10, usuario)
    servicio.avanzar_tiempo(partido, usuario)
    servicio.terminar(partido, usuario)
    hechos = registros(partido)
    assert [q for q, _, _ in hechos] == [
        "Empezó el partido",
        "Juega",
        "Gol",
        "Borró: Gol",
        "Dorsal",
        "Fin del 1.er tiempo",
        "Terminó el partido",
    ]
    assert all(quien == "ana" for _, _, quien in hechos)
    dorsal = Registro.objects.get(partido=partido, que="Dorsal")
    assert (dorsal.antes, dorsal.despues, dorsal.jugador) == ("1", "10", jugador)


@pytest.mark.django_db
def test_la_ficha_muestra_el_historial(client: Client, partido: Partido, usuario: User) -> None:
    servicio.empezar(partido, usuario)
    client.force_login(usuario)
    html = client.get(f"/partidos/{partido.pk}/ficha/").content.decode()
    assert "Historial" in html
    assert "Empezó el partido" in html
    assert "ana" in html


@pytest.mark.django_db
def test_mas_tiene_el_historial_del_torneo(client: Client, partido: Partido, usuario: User) -> None:
    servicio.empezar(partido, usuario)
    client.force_login(usuario)
    assert "/historial/" in client.get("/mas/").content.decode()
    html = client.get("/historial/").content.decode()
    assert "Empezó el partido" in html
    assert f"/partidos/{partido.pk}/ficha/" in html
