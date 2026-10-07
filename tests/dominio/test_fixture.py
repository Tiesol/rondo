"""FIX-06 y FIX-08: sorteo de series y fixture completo de una categoría."""

from collections import Counter
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dominio.fixture import SeriesInvalidas, armar_fixture, sortear_series
from dominio.formatos import cargar_formatos

FORMATOS = cargar_formatos(
    Path(__file__).resolve().parents[2] / "datos" / "config" / "formatos.json"
)


def club_por_decena(equipo: int) -> str:
    return f"club {equipo // 10}"


def test_fix_06_la_misma_semilla_da_el_mismo_sorteo() -> None:
    equipos = list(range(1, 9))
    uno = sortear_series(equipos, (4, 4), str, semilla=7, separar_clubes=True)
    otro = sortear_series(equipos, (4, 4), str, semilla=7, separar_clubes=True)
    assert uno == otro
    assert sorted(len(s) for s in uno.values()) == [4, 4]
    assert list(uno) == ["A", "B"]


@given(semilla=st.integers(min_value=0, max_value=10_000))
def test_fix_06_separa_a_los_del_mismo_club(semilla: int) -> None:
    equipos = [10, 11, 20, 21, 30, 40, 50, 60]  # dos clubes con dos equipos
    series = sortear_series(equipos, (4, 4), club_por_decena, semilla=semilla, separar_clubes=True)
    for serie in series.values():
        clubes = Counter(club_por_decena(e) for e in serie)
        assert max(clubes.values()) == 1


def test_fix_06_si_no_se_puede_separar_reparte_lo_mas_posible() -> None:
    equipos = [10, 11, 12, 20, 30, 40]  # tres del mismo club y dos series
    series = sortear_series(equipos, (3, 3), club_por_decena, semilla=1, separar_clubes=True)
    del_club_1 = [sum(e // 10 == 1 for e in s) for s in series.values()]
    assert sorted(del_club_1) == [1, 2]


def test_fix_06_con_la_regla_apagada_es_solo_azar() -> None:
    equipos = list(range(1, 9))
    series = sortear_series(equipos, (4, 4), str, semilla=3, separar_clubes=False)
    assert sorted(e for s in series.values() for e in s) == equipos


@pytest.mark.parametrize("n", range(2, 11))
def test_el_fixture_tiene_los_partidos_del_formato(n: int) -> None:
    formato = FORMATOS.para(n)
    fixture = armar_fixture(
        formato,
        list(range(1, n + 1)),
        str,
        semilla=5,
        separar_clubes=True,
        mismo_club_fecha_1=True,
    )
    assert len(fixture.partidos) == formato.total_de_partidos
    grupos = [p for p in fixture.partidos if p.fase == "grupos"]
    eliminacion = [p for p in fixture.partidos if p.fase == "eliminacion"]
    assert all(p.local is not None and p.fecha is not None for p in grupos)
    assert len(eliminacion) == len(formato.eliminacion)


def test_fix_08_la_eliminacion_tiene_participantes_por_definir() -> None:
    fixture = armar_fixture(
        FORMATOS.para(8),
        list(range(1, 9)),
        str,
        semilla=5,
        separar_clubes=True,
        mismo_club_fecha_1=True,
    )
    final = next(p for p in fixture.partidos if p.clave == "oro_final")
    assert (final.local, final.visitante) == (None, None)
    assert (final.texto_local, final.texto_visitante) == (
        "Ganador de la semi 1 de Oro",
        "Ganador de la semi 2 de Oro",
    )
    assert (final.copa, final.ronda, final.nombre) == ("oro", "final", "Final de Oro")


def test_las_series_elegidas_a_mano_se_respetan() -> None:
    a, b = [1, 2, 3], [4, 5, 6]
    fixture = armar_fixture(
        FORMATOS.para(6),
        a + b,
        str,
        semilla=5,
        separar_clubes=True,
        mismo_club_fecha_1=True,
        series={"A": a, "B": b},
    )
    assert fixture.series == {"A": a, "B": b}
    for partido in fixture.partidos:
        if partido.fase == "grupos":
            assert {partido.local in a, partido.visitante in a} == {True, False}


def test_series_con_otro_tamanio_dan_un_error_claro() -> None:
    with pytest.raises(SeriesInvalidas, match="4 y 4"):
        armar_fixture(
            FORMATOS.para(8),
            list(range(1, 9)),
            str,
            semilla=5,
            separar_clubes=True,
            mismo_club_fecha_1=True,
            series={"A": [1, 2, 3, 4, 5], "B": [6, 7, 8]},
        )


def test_todos_contra_todos_no_tiene_series() -> None:
    fixture = armar_fixture(
        FORMATOS.para(5),
        list(range(1, 6)),
        str,
        semilla=5,
        separar_clubes=True,
        mismo_club_fecha_1=True,
    )
    assert fixture.series == {}
