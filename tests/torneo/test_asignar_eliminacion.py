"""T6.1: el organizador asigna a mano los participantes de la eliminación (P50)."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Partido, Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture


@pytest.fixture
def sub9() -> CategoriaNivel:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(6):
        club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
        Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}")
    generar_fixture(cn, semilla=1)
    return cn


def entrar(client: Client, grupo: str) -> Client:
    usuario = User.objects.create_user(grupo[:4], password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


def semi(categoria: CategoriaNivel) -> Partido:
    return Partido.objects.get(categoria=categoria, clave="oro_semi_1")


@pytest.mark.django_db
def test_la_organizacion_asigna_y_la_referencia_queda_a_la_vista(
    client: Client, sub9: CategoriaNivel
) -> None:
    a, b = Equipo.objects.filter(categoria=sub9).order_by("pk")[:2]
    org = entrar(client, ORGANIZACION)
    respuesta = org.post(f"/partidos/{semi(sub9).pk}/asignar/", {"local": a.pk, "visitante": b.pk})
    assert respuesta["Location"] == f"/torneo/{sub9.pk}/fixture/"
    partido = semi(sub9)
    assert (partido.local, partido.visitante) == (a, b)
    html = org.get(f"/torneo/{sub9.pk}/fixture/").content.decode()
    assert a.nombre in html and "1.º A" in html


@pytest.mark.django_db
def test_no_el_mismo_equipo_a_los_dos_lados(client: Client, sub9: CategoriaNivel) -> None:
    a = Equipo.objects.filter(categoria=sub9).first()
    assert a is not None
    respuesta = entrar(client, ORGANIZACION).post(
        f"/partidos/{semi(sub9).pk}/asignar/", {"local": a.pk, "visitante": a.pk}, follow=True
    )
    assert "dos equipos distintos" in respuesta.content.decode()
    assert semi(sub9).local is None


@pytest.mark.django_db
def test_no_un_equipo_de_otra_categoria(client: Client, sub9: CategoriaNivel) -> None:
    otra = sub9.torneo.categorias.get(categoria="Sub 10", nivel="avanzado")
    ajeno = Equipo.objects.create(club=Club.objects.first(), categoria=otra, nombre="Ajeno")  # type: ignore[misc]
    a = Equipo.objects.filter(categoria=sub9).first()
    assert a is not None
    entrar(client, ORGANIZACION).post(
        f"/partidos/{semi(sub9).pk}/asignar/", {"local": a.pk, "visitante": ajeno.pk}
    )
    assert semi(sub9).visitante is None


@pytest.mark.django_db
def test_solo_la_eliminacion_se_asigna_y_solo_la_organizacion(
    client: Client, sub9: CategoriaNivel
) -> None:
    de_grupos = Partido.objects.filter(categoria=sub9, fase="grupos").first()
    assert de_grupos is not None
    org = entrar(client, ORGANIZACION)
    assert org.post(f"/partidos/{de_grupos.pk}/asignar/", {}).status_code == 404
    client.logout()
    mesa = User.objects.create_user("mesa", password="x")
    mesa.groups.add(Group.objects.get(name=MESA))
    client.force_login(mesa)
    assert client.post(f"/partidos/{semi(sub9).pk}/asignar/", {}).status_code == 403
