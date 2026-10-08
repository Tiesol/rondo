"""T3.4: modelos Serie y Partido, y servicio de fixture (FIX-09). Datos inventados."""

import io

import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import IntegrityError, transaction

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Partido, Serie, Torneo
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import (
    FixtureNoSePuede,
    generar_fixture,
    generar_fixtures_faltantes,
)


@pytest.fixture
def torneo() -> Torneo:
    return cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))


def categoria_con(torneo: Torneo, cantidad: int, categoria: str = "Sub 9") -> CategoriaNivel:
    cn: CategoriaNivel = torneo.categorias.get(categoria=categoria, nivel="avanzado")
    for i in range(cantidad):
        club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
        Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}")
    return cn


@pytest.mark.django_db
def test_seis_equipos_dan_dos_series_de_tres_y_catorce_partidos(torneo: Torneo) -> None:
    cn = categoria_con(torneo, 6)
    generar_fixture(cn)
    assert sorted(s.equipos.count() for s in cn.series.all()) == [3, 3]
    assert cn.partidos.count() == 14
    por_definir = cn.partidos.filter(local__isnull=True)
    assert por_definir.count() == 5
    assert set(por_definir.values_list("fase", flat=True)) == {"eliminacion"}
    final = cn.partidos.get(clave="oro_final")
    assert final.texto_local == "Ganador de la semi 1 de Oro"
    grupos = cn.partidos.filter(fase="grupos")
    assert all(p.fecha and p.local_id and p.visitante_id for p in grupos)
    assert set(grupos.values_list("estado", flat=True)) == {"pendiente"}


@pytest.mark.django_db
def test_rehacer_no_duplica(torneo: Torneo) -> None:
    cn = categoria_con(torneo, 6)
    generar_fixture(cn)
    generar_fixture(cn)
    assert cn.partidos.count() == 14
    assert cn.series.count() == 2


@pytest.mark.django_db
def test_fix_09_no_se_rehace_con_partidos_jugados(torneo: Torneo) -> None:
    cn = categoria_con(torneo, 4)
    generar_fixture(cn)
    cn.partidos.filter(fase="grupos").update(estado="jugado")
    with pytest.raises(FixtureNoSePuede, match="jugados"):
        generar_fixture(cn)


@pytest.mark.django_db
def test_fix_09_no_se_rehace_si_la_regla_lo_impide(torneo: Torneo) -> None:
    torneo.reglas = torneo.reglas | {"rehacer_fixture": False}
    torneo.save()
    cn = categoria_con(torneo, 4)
    generar_fixture(cn)
    with pytest.raises(FixtureNoSePuede, match="regla"):
        generar_fixture(cn)


@pytest.mark.django_db
def test_con_mas_de_diez_equipos_avisa_p27_y_no_guarda(torneo: Torneo) -> None:
    cn = categoria_con(torneo, 11)
    with pytest.raises(FixtureNoSePuede, match="P27"):
        generar_fixture(cn)
    assert not Partido.objects.exists()


@pytest.mark.django_db
def test_con_menos_de_dos_equipos_no_hay_fixture(torneo: Torneo) -> None:
    cn = categoria_con(torneo, 1)
    with pytest.raises(FixtureNoSePuede, match="al menos 2"):
        generar_fixture(cn)


@pytest.mark.django_db
def test_las_series_guardadas_se_respetan(torneo: Torneo) -> None:
    cn = categoria_con(torneo, 6)
    equipos = list(cn.equipos.order_by("pk"))
    a = Serie.objects.create(categoria=cn, nombre="A")
    a.equipos.set(equipos[:3])
    b = Serie.objects.create(categoria=cn, nombre="B")
    b.equipos.set(equipos[3:])
    generar_fixture(cn)
    serie_a = set(cn.series.get(nombre="A").equipos.all())
    assert serie_a == set(equipos[:3])
    for partido in cn.partidos.filter(fase="grupos"):
        assert (partido.local in serie_a) != (partido.visitante in serie_a)


@pytest.mark.django_db
def test_nuevo_sorteo_cambia_las_series(torneo: Torneo) -> None:
    cn = categoria_con(torneo, 8)
    generar_fixture(cn)
    antes = {s.nombre: set(s.equipos.all()) for s in cn.series.all()}
    distintas = False
    for semilla in range(1, 6):
        generar_fixture(cn, nuevo_sorteo=True, semilla=semilla)
        despues = {s.nombre: set(s.equipos.all()) for s in cn.series.all()}
        distintas = distintas or despues != antes
    assert distintas


@pytest.mark.django_db
def test_generar_los_faltantes_no_pisa_y_junta_los_problemas(torneo: Torneo) -> None:
    sub9 = categoria_con(torneo, 4)
    sub10 = categoria_con(torneo, 5, "Sub 10")
    sub11 = categoria_con(torneo, 11, "Sub 11")
    generar_fixture(sub9)
    sub9.partidos.update(estado="jugado")
    resultado = generar_fixtures_faltantes(torneo)
    assert resultado.generadas == [sub10]
    assert [c for c, _ in resultado.problemas] == [sub11]
    assert sub10.partidos.count() == 12


@pytest.mark.django_db
def test_local_y_visitante_distintos_en_la_base(torneo: Torneo) -> None:
    cn = categoria_con(torneo, 2)
    equipo = cn.equipos.first()
    with pytest.raises(IntegrityError), transaction.atomic():
        Partido.objects.create(categoria=cn, fase="grupos", fecha=1, local=equipo, visitante=equipo)


@pytest.mark.django_db
def test_la_demo_se_rehace_aunque_tenga_fixture() -> None:
    call_command("generar_demo", "--soy-la-demo", stdout=io.StringIO())
    torneo = Torneo.objects.get(es_demo=True)
    generar_fixtures_faltantes(torneo)
    assert Partido.objects.exists()
    call_command("generar_demo", "--soy-la-demo", stdout=io.StringIO())
    assert not Partido.objects.exists()
