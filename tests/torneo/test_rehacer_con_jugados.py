"""T11.15 (P44, P80): rehacer el fixture con partidos jugados, conservando los resultados.
Datos inventados."""

from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Evento, Partido, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture, motivo_desactualizado


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 6
    settings.PROGRAMADOR_TRABAJADORES = 2


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


@pytest.fixture
def con_fecha_1_jugada() -> CategoriaNivel:
    """Siete equipos (series cruzadas de 4 y 3), la fecha 1 jugada, y llega un 8.º."""
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(7):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
    generar_fixture(cn, semilla=3)
    for partido in cn.partidos.filter(fase="grupos", fecha=1):
        partido.estado = Partido.Estado.JUGADO
        partido.save()
        assert partido.local is not None
        Evento.objects.create(partido=partido, tipo="gol", equipo=partido.local)
    Equipo.objects.create(club=Club.objects.create(nombre="Club 8"), categoria=cn, nombre="Nuevo")
    return cn


@pytest.mark.django_db
def test_la_vista_previa_dice_que_se_conserva(
    org: Client, con_fecha_1_jugada: CategoriaNivel
) -> None:
    cn = con_fecha_1_jugada
    assert motivo_desactualizado(cn)
    pestana = org.get(f"/torneo/{cn.pk}/fixture/").content.decode()
    assert f"/torneo/{cn.pk}/rehacer/" in pestana
    html = org.get(f"/torneo/{cn.pk}/rehacer/").content.decode()
    assert "Se conservan 3" in html
    assert "Se borran" not in html
    # La vista previa no toca nada: siguen las series de 4 y 3.
    assert sorted(s.equipos.count() for s in cn.series.all()) == [3, 4]


@pytest.mark.django_db
def test_al_confirmar_los_jugados_siguen_con_sus_goles(
    org: Client, con_fecha_1_jugada: CategoriaNivel
) -> None:
    cn = con_fecha_1_jugada
    jugados = set(cn.partidos.filter(estado="jugado").values_list("pk", flat=True))
    respuesta = org.post(f"/torneo/{cn.pk}/rehacer/")
    assert respuesta.status_code == 302
    assert set(cn.partidos.filter(estado="jugado").values_list("pk", flat=True)) == jugados
    assert Evento.objects.filter(partido__in=jugados).count() == 3
    # Ocho equipos: dos series de 4, todos contra todos adentro (12 partidos de grupos).
    assert cn.partidos.filter(fase="grupos").count() == 12
    assert sorted(len(s.equipos.all()) for s in cn.series.all()) == [4, 4]
    for partido in cn.partidos.filter(pk__in=jugados).select_related("serie"):
        assert partido.serie is not None
        assert {partido.local_id, partido.visitante_id} <= set(
            partido.serie.equipos.values_list("pk", flat=True)
        )
    assert motivo_desactualizado(cn) == ""
