"""T2.5: pantallas de equipos (lista por categoría, alta y ficha). Datos inventados."""

from datetime import date

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Jugador, Persona, Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion


@pytest.fixture
def torneo() -> Torneo:
    return cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))


@pytest.fixture
def sub9(torneo: Torneo) -> CategoriaNivel:
    return torneo.categorias.get(categoria="Sub 9", nivel="avanzado")


@pytest.fixture
def river() -> Club:
    return Club.objects.create(nombre="River Plate")


def entrar(client: Client, grupo: str | None) -> Client:
    usuario = User.objects.create_user("u", password="x")
    if grupo:
        usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


def con_jugadores(equipo: Equipo, cantidad: int, **datos: object) -> None:
    for i in range(cantidad):
        persona = Persona.objects.create(
            tipo_documento="ci",
            documento=f"{5000000 + equipo.pk * 100 + i}",
            clave_documento=f"{5000000 + equipo.pk * 100 + i}",
            nombres="Nombre",
            apellidos=f"Inventado {i}",
            nacimiento=date(2017, 1, 1),
        )
        Jugador.objects.create(persona=persona, equipo=equipo, dorsal=i + 1, **datos)


@pytest.mark.django_db
@pytest.mark.parametrize("grupo", [ORGANIZACION, MESA])
def test_la_organizacion_y_la_mesa_crean_equipos(
    client: Client, sub9: CategoriaNivel, river: Club, grupo: str
) -> None:
    respuesta = entrar(client, grupo).post(
        f"/torneo/{sub9.pk}/equipos/nuevo/",
        {
            "club": river.pk,
            "categoria": sub9.pk,
            "nombre": "",
            "color_1": "#c8102e",
            "color_2": "#ffffff",
        },
    )
    equipo = Equipo.objects.get()
    assert respuesta["Location"] == f"/equipos/{equipo.pk}/plantel/"
    assert (equipo.club, equipo.categoria, equipo.nombre) == (river, sub9, "River Plate")
    assert equipo.color_1 == "#c8102e"


@pytest.mark.django_db
def test_sin_rol_no_se_crean_equipos(client: Client, sub9: CategoriaNivel) -> None:
    respuesta = entrar(client, None).get(f"/torneo/{sub9.pk}/equipos/nuevo/")
    assert respuesta.status_code == 403
    assert "Solo la organización puede cargar equipos" in respuesta.content.decode()


@pytest.mark.django_db
def test_el_club_sale_del_catalogo(client: Client, sub9: CategoriaNivel) -> None:
    respuesta = entrar(client, MESA).post(
        f"/torneo/{sub9.pk}/equipos/nuevo/",
        {"club": 999, "categoria": sub9.pk, "nombre": "Inventado"},
    )
    assert respuesta.status_code == 200
    assert respuesta.context["form"].errors["club"]


@pytest.mark.django_db
def test_un_equipo_repetido_muestra_el_error(
    client: Client, sub9: CategoriaNivel, river: Club
) -> None:
    Equipo.objects.create(club=river, categoria=sub9, nombre="River Plate")
    respuesta = entrar(client, MESA).post(
        f"/torneo/{sub9.pk}/equipos/nuevo/",
        {"club": river.pk, "categoria": sub9.pk, "nombre": "River Plate"},
    )
    assert respuesta.status_code == 200
    assert "Ya hay un equipo" in str(respuesta.context["form"].errors)


@pytest.mark.django_db
def test_la_lista_cuenta_jugadores_y_marca_los_que_faltan(
    client: Client, sub9: CategoriaNivel, river: Club
) -> None:
    corto = Equipo.objects.create(club=river, categoria=sub9, nombre="River Plate")
    lleno = Equipo.objects.create(club=river, categoria=sub9, nombre="River Plate 2")
    con_jugadores(corto, 3)
    con_jugadores(lleno, 12)
    html = entrar(client, MESA).get(f"/torneo/{sub9.pk}/equipos/").content.decode()
    assert "3 de 14 jugadores" in html
    assert "Faltan 9" in html
    assert "12 de 14 jugadores" in html
    assert f'href="/equipos/{corto.pk}/plantel/"' in html
    assert 'href="/torneo/' in html and "/equipos/nuevo/" in html


@pytest.mark.django_db
def test_la_ficha_muestra_el_plantel_y_sus_estados(
    client: Client, sub9: CategoriaNivel, river: Club
) -> None:
    equipo = Equipo.objects.create(club=river, categoria=sub9, nombre="River Plate")
    con_jugadores(equipo, 2)
    Jugador.objects.filter(equipo=equipo, dorsal=2).update(dorsal=None)
    html = entrar(client, MESA).get(f"/equipos/{equipo.pk}/plantel/").content.decode()
    assert "Inventado 0" in html
    assert "2 de 14 jugadores" in html
    assert "2 sin verificar" in html
    assert "1 sin dorsal" in html


@pytest.mark.django_db
def test_la_ficha_tiene_cuerpo_tecnico_y_404_si_no_existe(
    client: Client, sub9: CategoriaNivel, river: Club
) -> None:
    equipo = Equipo.objects.create(club=river, categoria=sub9, nombre="River Plate")
    mesa = entrar(client, MESA)
    assert (
        "Todavía no hay cuerpo técnico"
        in mesa.get(f"/equipos/{equipo.pk}/cuerpo-tecnico/").content.decode()
    )
    assert mesa.get("/equipos/999/plantel/").status_code == 404
    assert mesa.get(f"/equipos/{equipo.pk}/otra/").status_code == 404


@pytest.mark.django_db
def test_inicio_cuenta_categorias_sin_equipos_y_equipos_cortos(
    client: Client, torneo: Torneo, sub9: CategoriaNivel, river: Club
) -> None:
    Equipo.objects.create(club=river, categoria=sub9, nombre="River Plate")
    html = entrar(client, MESA).get("/").content.decode()
    assert "22 categorías sin equipos" in html
    assert "1 equipo debajo del mínimo de jugadores" in html
