"""T10.11: el dorsal se cambia de un partido a otro, desde la ficha del partido."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Jugador, Partido, Persona, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture


@pytest.fixture
def partido() -> Partido:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        equipo = Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
        for d in (7, 10):
            persona = Persona.objects.create(nombres=f"N{i}{d}", apellidos="Inventado")
            Jugador.objects.create(persona=persona, equipo=equipo, dorsal=d)
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


@pytest.mark.django_db
def test_la_plantilla_2026_no_exige_dorsal() -> None:
    assert cargar_config(settings.PLANTILLA_TORNEO).reglas.dorsal_obligatorio == "nunca"


@pytest.mark.django_db
def test_cambiar_el_dorsal_desde_la_ficha(org: Client, partido: Partido) -> None:
    assert partido.local is not None
    jugador = partido.local.jugadores.get(dorsal=7)
    url = f"/partidos/{partido.pk}/ficha/accion/"
    org.post(url, {"accion": "dorsal", "jugador": jugador.pk, "dorsal": "23"})
    jugador.refresh_from_db()
    assert jugador.dorsal == 23
    # Un dorsal que ya usa otro del equipo no se acepta.
    repetido = {"accion": "dorsal", "jugador": jugador.pk, "dorsal": "10"}
    respuesta = org.post(url, repetido, follow=True)
    jugador.refresh_from_db()
    assert jugador.dorsal == 23 and "ya lo usa" in respuesta.content.decode()
    # Vacío: sin dorsal.
    org.post(url, {"accion": "dorsal", "jugador": jugador.pk, "dorsal": ""})
    jugador.refresh_from_db()
    assert jugador.dorsal is None
