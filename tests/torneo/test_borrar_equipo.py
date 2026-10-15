"""T13.3: borrar un club, borrar un equipo y corregir uno mal cargado. Datos inventados."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import (
    CategoriaNivel,
    Club,
    Equipo,
    EquipoDeClub,
    Jugador,
    Partido,
    Persona,
    Profe,
    Torneo,
)
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.clubes import NoSePuede, borrar_club
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.equipos import borrar_equipo, cambiar_equipo
from torneo.servicios.fixture import generar_fixture, motivo_desactualizado


@pytest.fixture
def torneo() -> Torneo:
    return cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))


@pytest.fixture
def sub9(torneo: Torneo) -> CategoriaNivel:
    return torneo.categorias.get(categoria="Sub 9", nivel="avanzado")


def entrar(client: Client, rol: str) -> Client:
    usuario = User.objects.create_user(rol[:4], password="x")
    usuario.groups.add(Group.objects.get(name=rol))
    client.force_login(usuario)
    return client


def equipos(categoria: CategoriaNivel, cuantos: int) -> list[Equipo]:
    return [
        Equipo.objects.create(
            club=Club.objects.get_or_create(nombre=f"Club {i}")[0],
            categoria=categoria,
            nombre=f"Equipo {i}",
        )
        for i in range(cuantos)
    ]


def jugador(equipo: Equipo, nombre: str, documento: str) -> Persona:
    persona = Persona.objects.create(
        nombres=nombre, apellidos="Prueba", anio_nacimiento=2017, clave_documento=documento
    )
    Jugador.objects.create(equipo=equipo, persona=persona)
    return persona


# ---------- Club ----------


@pytest.mark.django_db
def test_un_club_sin_equipos_se_borra(client: Client) -> None:
    club = Club.objects.create(nombre="Club Vacío")
    EquipoDeClub.objects.create(club=club, nombre="Sin categorías")
    org = entrar(client, ORGANIZACION)
    pide = org.post(f"/clubes/{club.pk}/borrar/")
    assert pide.status_code == 200 and "Se borra" in pide.content.decode()
    assert Club.objects.filter(pk=club.pk).exists()
    respuesta = org.post(f"/clubes/{club.pk}/borrar/", {"confirmado": "1"})
    assert respuesta.status_code == 302
    assert not Club.objects.filter(pk=club.pk).exists()
    assert not EquipoDeClub.objects.exists()


@pytest.mark.django_db
def test_un_club_con_equipos_no_se_borra_y_dice_por_que(sub9: CategoriaNivel) -> None:
    (equipo,) = equipos(sub9, 1)
    with pytest.raises(NoSePuede, match="Sub 9"):
        borrar_club(equipo.club)
    assert Club.objects.filter(pk=equipo.club_id).exists()


# ---------- Equipo ----------


@pytest.mark.django_db
def test_borrar_un_equipo_sin_fixture_borra_su_plantel(sub9: CategoriaNivel) -> None:
    uno, otro = equipos(sub9, 2)
    solo_aca = jugador(uno, "Ana", "100")
    en_los_dos = jugador(uno, "Bea", "200")
    Jugador.objects.create(equipo=otro, persona=en_los_dos)
    Profe.objects.create(
        equipo=uno,
        persona=Persona.objects.create(nombres="Profe", apellidos="Uno"),
        rol="entrenador",
    )
    borrar_equipo(uno)
    assert not Equipo.objects.filter(pk=uno.pk).exists()
    assert not Jugador.objects.filter(equipo_id=uno.pk).exists()
    assert not Profe.objects.filter(equipo_id=uno.pk).exists()
    # Son datos de menores: la persona que solo estaba en ese equipo se borra.
    assert not Persona.objects.filter(pk=solo_aca.pk).exists()
    assert Persona.objects.filter(pk=en_los_dos.pk).exists()
    assert not Persona.objects.filter(nombres="Profe").exists()


@pytest.mark.django_db
def test_borrar_un_equipo_con_fixture_lo_deja_desactualizado(sub9: CategoriaNivel) -> None:
    lista = equipos(sub9, 5)
    generar_fixture(sub9, semilla=1)
    assert motivo_desactualizado(sub9) == ""
    borrado = lista[0].pk
    borrar_equipo(lista[0])
    assert not Partido.objects.filter(local_id=borrado).exists()
    assert not Partido.objects.filter(visitante_id=borrado).exists()
    assert motivo_desactualizado(sub9) != ""


@pytest.mark.django_db
def test_con_un_partido_jugado_no_se_borra(sub9: CategoriaNivel) -> None:
    lista = equipos(sub9, 4)
    generar_fixture(sub9, semilla=1)
    partido = Partido.objects.filter(local=lista[0]).first() or Partido.objects.get(
        visitante=lista[0], fecha=1
    )
    partido.estado = Partido.Estado.JUGADO
    partido.save()
    with pytest.raises(NoSePuede, match="jugado"):
        borrar_equipo(lista[0])
    assert Equipo.objects.filter(pk=lista[0].pk).exists()


@pytest.mark.django_db
def test_la_ficha_borra_con_confirmacion_y_vuelve_a_la_categoria(
    client: Client, sub9: CategoriaNivel
) -> None:
    (equipo,) = equipos(sub9, 1)
    jugador(equipo, "Ana", "100")
    org = entrar(client, ORGANIZACION)
    assert (
        f"/equipos/{equipo.pk}/borrar/"
        in org.get(f"/equipos/{equipo.pk}/plantel/").content.decode()
    )
    pide = org.post(f"/equipos/{equipo.pk}/borrar/").content.decode()
    assert "1 jugador" in pide
    respuesta = org.post(f"/equipos/{equipo.pk}/borrar/", {"confirmado": "1"})
    assert respuesta["Location"] == f"/torneo/{sub9.pk}/equipos/"
    assert not Equipo.objects.exists()


@pytest.mark.django_db
def test_la_mesa_no_borra(client: Client, sub9: CategoriaNivel) -> None:
    (equipo,) = equipos(sub9, 1)
    mesa = entrar(client, MESA)
    assert mesa.post(f"/equipos/{equipo.pk}/borrar/", {"confirmado": "1"}).status_code == 403
    assert mesa.post(f"/clubes/{equipo.club_id}/borrar/", {"confirmado": "1"}).status_code == 403
    assert Equipo.objects.exists()


# ---------- Corregir un equipo mal cargado ----------


@pytest.mark.django_db
def test_cambiar_el_club_y_la_categoria_de_un_equipo(torneo: Torneo, sub9: CategoriaNivel) -> None:
    (equipo,) = equipos(sub9, 1)
    jugador(equipo, "Ana", "100")
    bueno = Club.objects.create(nombre="Club Correcto")
    sub10 = torneo.categorias.get(categoria="Sub 10", nivel="avanzado")
    cambiar_equipo(equipo, club=bueno, categoria=sub10, nombre="Correcto")
    equipo.refresh_from_db()
    assert (equipo.club, equipo.categoria, equipo.nombre) == (bueno, sub10, "Correcto")
    assert equipo.equipo_de_club.club == bueno and equipo.equipo_de_club.nombre == "Correcto"
    assert equipo.jugadores.count() == 1
    # El equipo del club viejo quedó sin categorías: se borra.
    assert not EquipoDeClub.objects.filter(nombre="Equipo 0").exists()


@pytest.mark.django_db
def test_cambiar_la_categoria_con_fixture_lo_saca_y_deja_desactualizado(
    torneo: Torneo, sub9: CategoriaNivel
) -> None:
    lista = equipos(sub9, 5)
    generar_fixture(sub9, semilla=1)
    sub10 = torneo.categorias.get(categoria="Sub 10", nivel="avanzado")
    cambiar_equipo(lista[0], club=lista[0].club, categoria=sub10, nombre=lista[0].nombre)
    assert not Partido.objects.filter(local=lista[0]).exists()
    assert motivo_desactualizado(sub9) != ""


@pytest.mark.django_db
def test_la_ficha_edita_el_equipo(client: Client, torneo: Torneo, sub9: CategoriaNivel) -> None:
    (equipo,) = equipos(sub9, 1)
    org = entrar(client, ORGANIZACION)
    url = f"/equipos/{equipo.pk}/editar/"
    assert url in org.get(f"/equipos/{equipo.pk}/plantel/").content.decode()
    datos = {
        "club": equipo.club_id,
        "categoria": sub9.pk,
        "nombre": "Nuevo nombre",
        "color_1": "#112233",
        "color_2": "#ffffff",
    }
    respuesta = org.post(url, datos)
    assert respuesta.status_code == 302
    equipo.refresh_from_db()
    assert (equipo.nombre, equipo.color_1) == ("Nuevo nombre", "#112233")
