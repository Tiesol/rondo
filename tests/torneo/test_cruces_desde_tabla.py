"""T8.8: los cruces de la eliminación salen de la tabla (P50). Datos inventados."""

from datetime import timedelta
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Bloqueo, CategoriaNivel, Club, Equipo, Partido, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios import partido as servicio
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.cruces import aplicar, proponer
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo
from torneo.servicios.tabla import tablas_de


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10
    settings.PROGRAMADOR_TRABAJADORES = 4


@pytest.fixture
def categoria() -> CategoriaNivel:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        club = Club.objects.create(nombre=f"Club {i}")
        Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}")
    generar_fixture(cn, semilla=1)
    return cn


def jugar(partido: Partido, goles_local: int, goles_visitante: int) -> None:
    servicio.empezar(partido, None)
    for _ in range(goles_local):
        servicio.anotar(partido, "gol", partido.local, None, None)  # type: ignore[arg-type]
    for _ in range(goles_visitante):
        servicio.anotar(partido, "gol", partido.visitante, None, None)  # type: ignore[arg-type]
    if partido.fase == "eliminacion" and goles_local == goles_visitante:
        servicio.penales(partido, 5, 4)
    servicio.terminar(partido, None)


def jugar_grupos(categoria: CategoriaNivel) -> list[Equipo]:
    """Equipo 0 gana todo, Equipo 1 todo menos contra el 0, y así: la tabla queda 0, 1, 2, 3."""
    for p in categoria.partidos.filter(fase="grupos"):
        assert p.local is not None and p.visitante is not None
        mejor_local = int(p.local.nombre[-1]) < int(p.visitante.nombre[-1])
        jugar(p, *((2, 0) if mejor_local else (0, 2)))
    return [Equipo.objects.get(categoria=categoria, nombre=f"Equipo {i}") for i in range(4)]


@pytest.mark.django_db
def test_con_los_grupos_terminados_propone_las_semis_segun_la_tabla(
    categoria: CategoriaNivel,
) -> None:
    primero, segundo, tercero, cuarto = jugar_grupos(categoria)
    propuesta = proponer(categoria)
    assert propuesta.problema == ""
    por_clave = {p.clave: cruce for p, cruce in propuesta.cruces}
    assert por_clave["oro_semi_1"] == (primero, cuarto)  # 1.º vs 4.º
    assert por_clave["oro_semi_2"] == (segundo, tercero)  # 2.º vs 3.º
    assert "oro_final" not in por_clave  # todavía no se jugaron las semis


@pytest.mark.django_db
def test_con_las_semis_jugadas_propone_las_finales(categoria: CategoriaNivel) -> None:
    jugar_grupos(categoria)
    aplicar(categoria, proponer(categoria))
    semi_1 = categoria.partidos.get(clave="oro_semi_1")
    semi_2 = categoria.partidos.get(clave="oro_semi_2")
    jugar(semi_1, 0, 1)  # gana el 4.º
    jugar(semi_2, 1, 1)  # penales 5 a 4: gana el 2.º
    por_clave = {p.clave: cruce for p, cruce in proponer(categoria).cruces}
    assert por_clave["oro_final"] == (semi_1.visitante, semi_2.local)
    assert por_clave["plata_final"] == (semi_1.local, semi_2.visitante)


@pytest.mark.django_db
def test_con_un_partido_sin_jugar_no_propone_y_dice_por_que(categoria: CategoriaNivel) -> None:
    pendiente = categoria.partidos.filter(fase="grupos").first()
    assert pendiente is not None
    for p in categoria.partidos.filter(fase="grupos").exclude(pk=pendiente.pk):
        jugar(p, 1, 0)
    propuesta = proponer(categoria)
    assert propuesta.cruces == [] and "1 partido de grupos" in propuesta.problema


@pytest.mark.django_db
def test_con_un_sorteo_pendiente_tampoco(categoria: CategoriaNivel) -> None:
    for p in categoria.partidos.filter(fase="grupos"):
        jugar(p, 0, 0)  # todos empatados: hace falta el sorteo
    assert tablas_de(categoria)[0].falta_sorteo
    propuesta = proponer(categoria)
    assert propuesta.cruces == [] and "sorteo" in propuesta.problema


@pytest.mark.django_db
def test_una_propuesta_que_choca_muestra_el_choque_antes_de_guardar(
    client: Client, categoria: CategoriaNivel
) -> None:
    primero, *_ = jugar_grupos(categoria)
    programar_torneo(categoria.torneo)
    semi = categoria.partidos.get(clave="oro_semi_1")
    assert semi.inicio is not None
    bloqueo = Bloqueo.objects.create(
        torneo=categoria.torneo,
        inicio=semi.inicio - timedelta(minutes=10),
        fin=semi.inicio + timedelta(minutes=30),
        motivo="Partido de la ACF inventado",
    )
    bloqueo.equipos.add(primero)
    propuesta = proponer(categoria)
    assert any("Partido de la ACF inventado" in c for c in propuesta.choques)
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    html = client.get(f"/torneo/{categoria.pk}/fixture/").content.decode()
    assert "Cruces desde la tabla" in html and "Partido de la ACF inventado" in html
    client.post(f"/torneo/{categoria.pk}/cruces/")
    semi.refresh_from_db()
    assert semi.local == primero  # se guarda igual: la organización decide si reprograma
