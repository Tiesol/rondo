"""T8.5: el resultado de un partido sale de sus eventos (B3, P23, P72)."""

import pytest

from dominio.partido import Evento, ResultadoInvalido, resultado


def gol(lado: str) -> Evento:
    return Evento("gol", lado)  # type: ignore[arg-type]


def test_el_marcador_sale_de_los_goles() -> None:
    assert resultado([gol("local"), gol("local"), gol("visitante")]).marcador == (2, 1)


def test_un_gol_en_contra_cuenta_para_el_rival() -> None:
    # P72: se anota a nombre del equipo que lo hizo, sin jugador, y suma para el otro.
    eventos = [gol("local"), gol("local"), Evento("gol_en_contra", "local")]
    assert resultado(eventos).marcador == (2, 1)


def test_las_tarjetas_no_cambian_el_marcador() -> None:
    eventos = [gol("visitante"), Evento("amarilla", "local"), Evento("roja", "visitante")]
    assert resultado(eventos).marcador == (0, 1)


def test_wo_da_el_marcador_de_la_regla_al_que_se_presento() -> None:
    # P23: 3 a 0 para el que se presentó, sin importar los eventos.
    assert resultado([gol("local")], no_se_presento="local", marcador_wo=(3, 0)).marcador == (0, 3)
    assert resultado([], no_se_presento="visitante", marcador_wo=(3, 0)).marcador == (3, 0)


def test_ganador_empate_y_penales() -> None:
    assert resultado([gol("local")]).ganador == "local"
    assert resultado([]).ganador is None
    con_penales = resultado([gol("local"), gol("visitante")], penales=(4, 3))
    assert con_penales.ganador == "local" and con_penales.marcador == (1, 1)


def test_en_la_eliminacion_un_empate_pide_penales() -> None:
    empate = [gol("local"), gol("visitante")]
    with pytest.raises(ResultadoInvalido, match="penales"):
        resultado(empate, eliminacion=True).revisar_para_terminar()
    resultado(empate, eliminacion=True, penales=(5, 4)).revisar_para_terminar()
    resultado(empate).revisar_para_terminar()  # en grupos, el empate vale


def test_penales_empatados_no_definen() -> None:
    with pytest.raises(ResultadoInvalido, match="penales"):
        resultado([], eliminacion=True, penales=(3, 3)).revisar_para_terminar()
