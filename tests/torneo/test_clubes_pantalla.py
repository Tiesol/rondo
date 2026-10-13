"""T11.6 (P10): pantalla de clubes. Crear, editar, alias y unir duplicados. Datos inventados."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.clubes import NoSePuede, unir_clubes
from torneo.servicios.configuracion import cargar_configuracion


@pytest.fixture
def torneo() -> Torneo:
    return cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


def equipo(torneo: Torneo, club: Club, categoria: str = "Sub 9", nombre: str = "") -> Equipo:
    cn: CategoriaNivel = torneo.categorias.get(categoria=categoria, nivel="avanzado")
    return Equipo.objects.create(club=club, categoria=cn, nombre=nombre or club.nombre)


@pytest.mark.django_db
def test_la_lista_muestra_los_clubes_y_se_llega_desde_mas(org: Client) -> None:
    Club.objects.create(nombre="Leones del Norte")
    assert "/clubes/" in org.get("/mas/").content.decode()
    html = org.get("/clubes/").content.decode()
    assert "Leones del Norte" in html


@pytest.mark.django_db
def test_crear_un_club_con_alias(org: Client) -> None:
    respuesta = org.post("/clubes/", {"nombre": "Tigres FC", "alias": "Tigres\nTFC"})
    assert respuesta.status_code == 302
    club = Club.objects.get(nombre="Tigres FC")
    assert club.alias == ["TFC", "Tigres"]


@pytest.mark.django_db
def test_no_se_repite_un_nombre(org: Client) -> None:
    Club.objects.create(nombre="Tigres FC")
    respuesta = org.post("/clubes/", {"nombre": "tigres fc", "alias": ""})
    assert respuesta.status_code == 200
    assert "Ya hay un club" in respuesta.content.decode()
    assert Club.objects.count() == 1


@pytest.mark.django_db
def test_editar_nombre_y_alias(org: Client) -> None:
    club = Club.objects.create(nombre="Tigre")
    respuesta = org.post(f"/clubes/{club.pk}/", {"nombre": "Tigres FC", "alias": "Tigre"})
    assert respuesta.status_code == 302
    club.refresh_from_db()
    assert (club.nombre, club.alias) == ("Tigres FC", ["Tigre"])


@pytest.mark.django_db
def test_unir_pasa_los_equipos_y_los_nombres_al_que_queda(org: Client, torneo: Torneo) -> None:
    bueno = Club.objects.create(nombre="Tigres FC", alias=["TFC"])
    repetido = Club.objects.create(nombre="Club Tigres", alias=["Tigres"])
    equipo(torneo, repetido, "Sub 9", "Tigres")
    respuesta = org.post(f"/clubes/{repetido.pk}/unir/", {"destino": bueno.pk})
    assert respuesta.status_code == 302
    assert not Club.objects.filter(pk=repetido.pk).exists()
    bueno.refresh_from_db()
    assert set(bueno.alias) == {"TFC", "Club Tigres", "Tigres"}
    assert Equipo.objects.get().club == bueno


@pytest.mark.django_db
def test_unir_avisa_si_quedarian_dos_equipos_iguales(torneo: Torneo) -> None:
    bueno = Club.objects.create(nombre="Tigres FC")
    repetido = Club.objects.create(nombre="Club Tigres")
    equipo(torneo, bueno, "Sub 9", "Tigres")
    equipo(torneo, repetido, "Sub 9", "Tigres")
    with pytest.raises(NoSePuede, match="Tigres"):
        unir_clubes(repetido, bueno)
    assert Club.objects.count() == 2


@pytest.mark.django_db
def test_sin_login_no_entra(client: Client) -> None:
    assert client.get("/clubes/").status_code == 302
