"""T11.13 (P83): penales tiro por tiro. 3 por equipo y, si siguen empatados, uno más por
equipo hasta que se defina."""

from typing import Literal

from dominio.penales import Tiro, estado_de_penales

L: Literal["local"] = "local"
V: Literal["visitante"] = "visitante"


def test_se_define_al_terminar_la_tanda() -> None:
    tiros: list[Tiro] = [(L, True), (V, True), (L, True), (V, True), (L, True), (V, False)]
    estado = estado_de_penales(tiros, por_equipo=3)
    assert (estado.local, estado.visitante, estado.ganador) == (3, 2, L)


def test_se_define_antes_si_el_otro_ya_no_alcanza() -> None:
    tiros: list[Tiro] = [(L, True), (V, False), (L, True), (V, False)]
    estado = estado_de_penales(tiros, por_equipo=3)
    assert estado.ganador == L  # 2 a 0 y al visitante le queda uno


def test_empatados_sigue_uno_por_equipo_hasta_definir() -> None:
    tanda: list[Tiro] = [(L, True), (V, True)] * 3
    estado = estado_de_penales([*tanda, (L, True), (V, True)], por_equipo=3)
    assert estado.ganador is None
    assert estado.muerte_subita
    estado = estado_de_penales([*tanda, (L, True), (V, False)], por_equipo=3)
    assert (estado.local, estado.visitante, estado.ganador) == (4, 3, L)


def test_a_quien_le_toca() -> None:
    assert estado_de_penales([], por_equipo=3).patea is None  # el que empiece
    estado = estado_de_penales([(V, True)], por_equipo=3)
    assert estado.patea == L
    estado = estado_de_penales([(V, True), (L, False)], por_equipo=3)
    assert estado.patea == V
