"""FIX-03 a FIX-05: cruces de la fase de grupos, con tests de propiedad."""

from collections import Counter
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dominio.cruces import Cruce, armar_grupos
from dominio.formatos import Grupos, cargar_formatos

FORMATOS = cargar_formatos(
    Path(__file__).resolve().parents[2] / "datos" / "config" / "formatos.json"
)


def series_de(grupos: Grupos, equipos: list[int]) -> dict[str, list[int]]:
    if not grupos.series:
        return {"": equipos}
    resultado, inicio = {}, 0
    for nombre, tamanio in zip(grupos.nombres_de_series, grupos.series, strict=True):
        resultado[nombre] = equipos[inicio : inicio + tamanio]
        inicio += tamanio
    return resultado


def cruces_para(n: int, clubes: dict[int, str] | None = None) -> tuple[Grupos, list[Cruce[int]]]:
    grupos = FORMATOS.para(n).grupos
    equipos = list(range(1, n + 1))
    club = (clubes or {}).get
    return grupos, armar_grupos(
        grupos, series_de(grupos, equipos), lambda e: club(e) or str(e), mismo_club_fecha_1=True
    )


@pytest.mark.parametrize("n", range(2, 11))
def test_fix_03_cada_cruce_una_vez_y_nadie_dos_veces_por_fecha(n: int) -> None:
    grupos, cruces = cruces_para(n)
    assert len(cruces) == grupos.cantidad_de_partidos(n)
    pares = Counter(frozenset((c.local, c.visitante)) for c in cruces)
    esperado = 2 if grupos.ida_y_vuelta else 1
    assert set(pares.values()) == {esperado}
    por_fecha = Counter((c.fecha, e) for c in cruces for e in (c.local, c.visitante))
    assert max(por_fecha.values()) == 1


@pytest.mark.parametrize("n", range(2, 11))
def test_fix_03_juegan_los_que_tienen_que_jugar(n: int) -> None:
    grupos, cruces = cruces_para(n)
    series = series_de(grupos, list(range(1, n + 1)))
    pares = {frozenset((c.local, c.visitante)) for c in cruces}
    if grupos.tipo == "series_cruzadas":
        a, b = series.values()
        assert pares == {frozenset((x, y)) for x in a for y in b}
    else:
        assert pares == {frozenset((x, y)) for s in series.values() for x in s for y in s if x != y}


def test_fix_03_ida_y_vuelta_invierte_la_localia() -> None:
    _, cruces = cruces_para(3)
    localias = Counter((c.local, c.visitante) for c in cruces)
    assert set(localias.values()) == {1}


def test_fix_04_con_4_y_3_descansa_uno_de_a_en_cada_fecha() -> None:
    grupos, cruces = cruces_para(7)
    a = series_de(grupos, list(range(1, 8)))["A"]
    fechas = sorted({c.fecha for c in cruces})
    assert fechas == [1, 2, 3, 4]
    for fecha in fechas:
        juegan = {e for c in cruces if c.fecha == fecha for e in (c.local, c.visitante)}
        assert len(set(a) - juegan) == 1


def test_fix_04_las_series_cruzadas_dicen_de_que_serie_es_cada_uno() -> None:
    _, cruces = cruces_para(6)
    assert {c.serie for c in cruces} == {"A-B"}


def test_las_fechas_empiezan_en_1_y_no_tienen_huecos() -> None:
    for n in range(2, 11):
        _, cruces = cruces_para(n)
        fechas = sorted({c.fecha for c in cruces})
        assert fechas == list(range(1, len(fechas) + 1))


@given(
    n=st.integers(min_value=2, max_value=10),
    datos=st.data(),
)
def test_fix_05_dos_del_mismo_club_se_enfrentan_en_la_fecha_1(n: int, datos: st.DataObject) -> None:
    _, cruces = cruces_para(n)
    pares = [(c.local, c.visitante) for c in cruces]
    a, b = datos.draw(st.sampled_from(pares))
    _, con_club = cruces_para(n, {a: "JMP", b: "JMP"})
    fecha_del_par = min(c.fecha for c in con_club if {c.local, c.visitante} == {a, b})
    assert fecha_del_par == 1


def test_fix_05_apagado_no_reordena() -> None:
    grupos = FORMATOS.para(4).grupos
    sin = armar_grupos(grupos, {"": [1, 2, 3, 4]}, str, mismo_club_fecha_1=False)
    con_club_apagado = armar_grupos(
        grupos,
        {"": [1, 2, 3, 4]},
        lambda e: "JMP" if e in (2, 3) else str(e),
        mismo_club_fecha_1=False,
    )
    assert sin == con_club_apagado
