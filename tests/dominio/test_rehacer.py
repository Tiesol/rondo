"""T11.15 (P44, P80: los resultados jugados cuentan): al cambiar la cantidad de equipos, las
series nuevas se eligen para que los partidos jugados sigan existiendo."""

from dominio.formatos import Grupos
from dominio.rehacer import planear_rehacer


def club(equipo: str) -> str:
    return equipo  # cada equipo de su club


def test_de_7_a_8_equipos_se_conserva_la_fecha_1() -> None:
    # Con 7: series cruzadas, A (a1..a4) contra B (b1..b3). Fecha 1: tres cruces A-B.
    jugados = [(1, "a1", "b1"), (2, "a2", "b2"), (3, "a3", "b3")]
    equipos = ["a1", "a2", "a3", "a4", "b1", "b2", "b3", "nuevo"]
    plan = planear_rehacer(Grupos(tipo="series", series=(4, 4)), equipos, jugados, club)
    assert set(plan.conservados) == {1, 2, 3}
    assert plan.descartados == ()
    assert plan.series is not None
    serie_de = {e: nombre for nombre, lista in plan.series.items() for e in lista}
    assert all(serie_de[a] == serie_de[b] for _, a, b in jugados)


def test_a_series_cruzadas_los_jugados_quedan_en_series_distintas() -> None:
    jugados = [(1, "e1", "e2"), (2, "e3", "e4")]
    equipos = ["e1", "e2", "e3", "e4", "e5", "e6"]
    plan = planear_rehacer(Grupos(tipo="series_cruzadas", series=(3, 3)), equipos, jugados, club)
    assert set(plan.conservados) == {1, 2}
    assert plan.series is not None
    serie_de = {e: nombre for nombre, lista in plan.series.items() for e in lista}
    assert all(serie_de[a] != serie_de[b] for _, a, b in jugados)


def test_si_no_hay_forma_se_descarta_lo_menos_posible() -> None:
    # Un triángulo no entra entero en series cruzadas: uno de los tres se pierde.
    jugados = [(1, "e1", "e2"), (2, "e2", "e3"), (3, "e1", "e3")]
    equipos = ["e1", "e2", "e3", "e4", "e5", "e6"]
    plan = planear_rehacer(Grupos(tipo="series_cruzadas", series=(3, 3)), equipos, jugados, club)
    assert len(plan.conservados) == 2
    assert len(plan.descartados) == 1


def test_todos_contra_todos_conserva_todo_y_un_equipo_que_se_va_se_descarta() -> None:
    jugados = [(1, "e1", "e2"), (2, "e3", "e4"), (3, "e5", "e1")]
    equipos = ["e1", "e2", "e3", "e4"]  # e5 ya no está
    plan = planear_rehacer(Grupos(tipo="todos_contra_todos"), equipos, jugados, club)
    assert plan.series is None
    assert set(plan.conservados) == {1, 2}
    assert plan.descartados == (3,)


def test_un_cruce_repetido_cuenta_una_vez_salvo_ida_y_vuelta() -> None:
    jugados = [(1, "e1", "e2"), (2, "e2", "e1")]
    equipos = ["e1", "e2", "e3", "e4"]
    plan = planear_rehacer(Grupos(tipo="todos_contra_todos"), equipos, jugados, club)
    assert (plan.conservados, plan.descartados) == ((1,), (2,))
    ida_y_vuelta = Grupos(tipo="todos_contra_todos", ida_y_vuelta=True)
    assert planear_rehacer(ida_y_vuelta, ["e1", "e2", "e3"], jugados, club).conservados == (1, 2)


def test_con_empate_separa_a_los_del_mismo_club() -> None:
    equipos = ["x1", "x2", "y1", "y2"]
    plan = planear_rehacer(Grupos(tipo="series", series=(2, 2)), equipos, [], lambda e: e[0])
    assert plan.series is not None
    for lista in plan.series.values():
        assert len({e[0] for e in lista}) == 2
