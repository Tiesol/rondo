"""T8.7: la tabla de posiciones de una categoría, desde los partidos cargados. Datos inventados."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Partido, Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios import partido as servicio
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.tabla import tablas_de


@pytest.fixture
def categoria() -> CategoriaNivel:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
    generar_fixture(cn, semilla=1)
    return cn


def jugar(partido: Partido, goles_local: int, goles_visitante: int) -> None:
    servicio.empezar(partido, None)
    for _ in range(goles_local):
        servicio.anotar(partido, "gol", partido.local, None, None)  # type: ignore[arg-type]
    for _ in range(goles_visitante):
        servicio.anotar(partido, "gol", partido.visitante, None, None)  # type: ignore[arg-type]
    servicio.terminar(partido, None)


@pytest.mark.django_db
def test_sin_partidos_jugados_todos_en_cero(categoria: CategoriaNivel) -> None:
    (unica,) = tablas_de(categoria)
    assert unica.nombre == "" and len(unica.filas) == 4
    assert all(f.pj == 0 and f.puntos == 0 for f in unica.filas)


@pytest.mark.django_db
def test_los_partidos_terminados_suman(categoria: CategoriaNivel) -> None:
    primero = categoria.partidos.filter(fase="grupos").first()
    assert primero is not None
    jugar(primero, 2, 0)
    en_juego = categoria.partidos.filter(fase="grupos").exclude(pk=primero.pk).first()
    assert en_juego is not None
    servicio.empezar(en_juego, None)  # en juego: todavía no cuenta
    servicio.anotar(en_juego, "gol", en_juego.local, None, None)  # type: ignore[arg-type]
    (unica,) = tablas_de(categoria)
    lider = unica.filas[0]
    assert (lider.equipo, lider.puntos, lider.gf) == (primero.local_id, 3, 2)
    assert sum(f.pj for f in unica.filas) == 2


@pytest.mark.django_db
def test_la_pestana_posiciones_muestra_la_tabla_y_pide_el_sorteo(
    client: Client, categoria: CategoriaNivel
) -> None:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    # T13.10: el sorteo se pide recién con la serie terminada (todos 1 a 1).
    for partido in categoria.partidos.filter(fase="grupos"):
        jugar(partido, 1, 1)
    html = client.get(f"/torneo/{categoria.pk}/posiciones/").content.decode()
    assert "Equipo 0" in html and "Pts" in html
    assert "Falta sorteo" in html  # empatados en todo: hasta el sorteo no se sabe el orden
    empatados = tablas_de(categoria)[0].falta_sorteo
    datos = {f"lugar_{e.pk}": str(i) for i, e in enumerate(empatados, start=1)}
    client.post(f"/torneo/{categoria.pk}/sorteo/", datos)
    assert not tablas_de(categoria)[0].falta_sorteo
    assert "Falta sorteo" not in client.get(f"/torneo/{categoria.pk}/posiciones/").content.decode()


@pytest.mark.django_db
def test_la_mesa_ve_la_tabla_pero_no_registra_el_sorteo(
    client: Client, categoria: CategoriaNivel
) -> None:
    usuario = User.objects.create_user("mesa", password="x")
    usuario.groups.add(Group.objects.get(name=MESA))
    client.force_login(usuario)
    assert client.get(f"/torneo/{categoria.pk}/posiciones/").status_code == 200
    assert client.post(f"/torneo/{categoria.pk}/sorteo/", {}).status_code == 403
