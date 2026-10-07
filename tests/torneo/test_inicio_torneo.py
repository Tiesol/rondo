"""TU.5: Inicio (torneo activo, pendientes y accesos) y Torneo (categoría y pestañas)."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion


def entrar(client: Client, grupo: str) -> Client:
    usuario = User.objects.create_user(grupo[:4], password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


@pytest.fixture
def torneo() -> Torneo:
    return cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))


@pytest.fixture
def sub9(torneo: Torneo) -> CategoriaNivel:
    return torneo.categorias.get(categoria="Sub 9", nivel="avanzado")


# ---------- Inicio ----------


@pytest.mark.django_db
def test_sin_torneo_la_organizacion_ve_la_invitacion_a_crearlo(client: Client) -> None:
    html = entrar(client, ORGANIZACION).get("/").content.decode()
    assert "Todavía no hay un torneo" in html
    assert 'href="/torneos/nuevo/"' in html


@pytest.mark.django_db
def test_sin_torneo_la_mesa_sabe_que_lo_crea_la_organizacion(client: Client) -> None:
    html = entrar(client, MESA).get("/").content.decode()
    assert "Todavía no hay un torneo" in html
    assert "/torneos/nuevo/" not in html


@pytest.mark.django_db
def test_con_torneo_muestra_su_banda_pendientes_y_accesos(client: Client, torneo: Torneo) -> None:
    html = entrar(client, ORGANIZACION).get("/").content.decode()
    assert "JMP CUP <span>2026</span>" in html
    assert "5.ª edición" in html
    assert "Pendientes" in html
    assert "sin equipos" in html
    assert f'href="/torneos/{torneo.pk}/reglas/"' in html
    assert 'href="/torneo/"' in html


@pytest.mark.django_db
def test_la_mesa_no_ve_el_acceso_a_las_reglas(client: Client, torneo: Torneo) -> None:
    html = entrar(client, MESA).get("/").content.decode()
    assert f"/torneos/{torneo.pk}/reglas/" not in html


@pytest.mark.django_db
def test_el_torneo_activo_es_el_mas_reciente(torneo: Torneo) -> None:
    Torneo.objects.create(
        nombre="Viejo",
        edicion=4,
        anio=2025,
        inicio=torneo.inicio.replace(year=2025),
        fin=torneo.fin.replace(year=2025),
    )
    assert Torneo.activo() == torneo


# ---------- Torneo ----------


@pytest.mark.django_db
def test_torneo_va_a_la_primera_categoria(client: Client, torneo: Torneo) -> None:
    respuesta = entrar(client, MESA).get("/torneo/")
    primera = torneo.categorias.first()
    assert primera is not None
    assert respuesta["Location"] == f"/torneo/{primera.pk}/equipos/"


@pytest.mark.django_db
def test_torneo_sin_torneo_vuelve_al_inicio(client: Client) -> None:
    assert entrar(client, MESA).get("/torneo/")["Location"] == "/"


@pytest.mark.django_db
def test_la_categoria_muestra_su_banda_selector_y_pestanas(
    client: Client, sub9: CategoriaNivel
) -> None:
    html = entrar(client, MESA).get(f"/torneo/{sub9.pk}/equipos/").content.decode()
    assert "Sub 9 <span>Avanzado</span>" in html
    assert "nacidos en 2017" in html
    assert f'href="/torneo/{sub9.pk}/equipos/" aria-current="page"' in html
    assert 'hx-push-url="true"' in html
    assert "Todavía no hay equipos" in html


@pytest.mark.django_db
def test_con_htmx_solo_vuelve_la_parte_de_la_categoria(
    client: Client, sub9: CategoriaNivel
) -> None:
    html = (
        entrar(client, MESA)
        .get(f"/torneo/{sub9.pk}/fixture/", headers={"HX-Request": "true"})
        .content.decode()
    )
    assert "<html" not in html
    assert 'id="categoria"' in html
    assert "Todavía no hay fixture" in html


@pytest.mark.django_db
def test_una_pestana_desconocida_es_404(client: Client, sub9: CategoriaNivel) -> None:
    assert entrar(client, MESA).get(f"/torneo/{sub9.pk}/inventada/").status_code == 404


@pytest.mark.django_db
def test_la_organizacion_cambia_los_ajustes(client: Client, sub9: CategoriaNivel) -> None:
    c3 = sub9.torneo.canchas.get(codigo="C3")
    respuesta = entrar(client, ORGANIZACION).post(
        f"/torneo/{sub9.pk}/ajustes/",
        {"min_jugadores": 11, "max_jugadores": 15, "min_por_tiempo": 20, "canchas": [c3.pk]},
    )
    assert respuesta.status_code == 302
    sub9.refresh_from_db()
    assert (sub9.min_jugadores, sub9.max_jugadores) == (11, 15)
    assert list(sub9.canchas.values_list("codigo", flat=True)) == ["C3"]


@pytest.mark.django_db
def test_ajustes_invalidos_muestran_el_error(client: Client, sub9: CategoriaNivel) -> None:
    respuesta = entrar(client, ORGANIZACION).post(
        f"/torneo/{sub9.pk}/ajustes/",
        {"min_jugadores": 14, "max_jugadores": 10, "min_por_tiempo": 20},
    )
    assert respuesta.status_code == 200
    assert respuesta.context["form"].errors["max_jugadores"]
    sub9.refresh_from_db()
    assert sub9.max_jugadores == 14


@pytest.mark.django_db
def test_la_mesa_ve_los_ajustes_pero_no_los_cambia(client: Client, sub9: CategoriaNivel) -> None:
    mesa = entrar(client, MESA)
    html = mesa.get(f"/torneo/{sub9.pk}/ajustes/").content.decode()
    assert "solo la organización puede cambiarlos" in html
    assert 'name="max_jugadores"' not in html
    assert "12 a 14" in html
    respuesta = mesa.post(f"/torneo/{sub9.pk}/ajustes/", {"max_jugadores": 20})
    assert respuesta.status_code == 403
