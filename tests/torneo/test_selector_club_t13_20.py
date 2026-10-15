"""T13.20: en "Un equipo no puede jugar", primero el club y después sus equipos, con la categoría
al lado. Con 93 equipos, la lista de todos no se maneja. Funciona sin JavaScript. Datos
inventados."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Bloqueo, Club, Equipo, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    for nombre in ("Norte FC", "Sur FC"):
        club = Club.objects.create(nombre=nombre)
        for categoria in ("Sub 9", "Sub 10"):
            Equipo.objects.create(
                club=club,
                categoria=torneo.categorias.get(categoria=categoria, nivel="inicial"),
                nombre=nombre.split()[0],
            )
    return torneo


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


@pytest.mark.django_db
def test_sin_club_elegido_no_lista_todos_los_equipos(org: Client, torneo: Torneo) -> None:
    html = org.get(f"/torneos/{torneo.pk}/acf/").content.decode()
    assert 'name="club"' in html and "Norte FC" in html and "Sur FC" in html
    assert 'name="equipos"' not in html


@pytest.mark.django_db
def test_con_el_club_elegido_marca_sus_equipos_con_la_categoria(
    org: Client, torneo: Torneo
) -> None:
    norte = Club.objects.get(nombre="Norte FC")
    html = org.get(f"/torneos/{torneo.pk}/acf/?club={norte.pk}").content.decode()
    assert html.count('name="equipos"') == 2
    assert 'type="checkbox"' in html
    assert "Sub 9 Inicial" in html and "Sub 10 Inicial" in html
    assert "Sur ·" not in html


@pytest.mark.django_db
def test_guardar_con_el_club(org: Client, torneo: Torneo) -> None:
    norte = Club.objects.get(nombre="Norte FC")
    equipos = list(Equipo.objects.filter(club=norte).values_list("pk", flat=True))
    respuesta = org.post(
        f"/torneos/{torneo.pk}/acf/?club={norte.pk}",
        {
            "club": norte.pk,
            "equipos": equipos,
            "dia": "2026-10-24",
            "desde": "09:00",
            "hasta": "12:00",
            "motivo": "Partido de la ACF",
        },
    )
    assert respuesta.status_code == 302
    assert sorted(Bloqueo.objects.get().equipos.values_list("pk", flat=True)) == sorted(equipos)
