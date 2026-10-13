"""T8.7: tabla de posiciones (CONTEXTO 4.6, P26, P28 y P34). Un test por criterio, en orden."""

from dominio.tabla import Jugado, Tarjetas, mejores, tabla

A, B, C, D = "A", "B", "C", "D"


def j(local: str, visitante: str, gl: int, gv: int) -> Jugado:
    return Jugado(local, visitante, gl, gv)


def orden(filas: list) -> list[str]:  # type: ignore[type-arg]
    return [f.equipo for f in filas]


def test_puntos_3_1_y_0_y_estadisticas() -> None:
    filas = tabla([A, B, C], [j(A, B, 2, 0), j(B, C, 1, 1), j(A, C, 0, 1)])
    a = next(f for f in filas if f.equipo == A)
    assert (a.pj, a.pg, a.pe, a.pp, a.gf, a.gc, a.dg, a.puntos) == (2, 1, 0, 1, 2, 1, 1, 3)
    assert orden(filas) == [C, A, B]  # C: 4 puntos, A: 3, B: 1


def test_los_puntos_se_configuran() -> None:
    filas = tabla([A, B], [j(A, B, 1, 1)], puntos=(2, 1))
    assert [f.puntos for f in filas] == [1, 1]


def test_1_empatados_en_puntos_manda_el_partido_entre_ellos() -> None:
    # A y B con 4 puntos; B le ganó a A: B primero, aunque A tenga más goles en total.
    partidos = [j(A, B, 0, 1), j(A, C, 5, 0), j(A, D, 0, 0), j(B, C, 0, 1), j(B, D, 0, 0)]
    filas = tabla([A, B, C, D], partidos)
    assert orden(filas)[:2] == [B, A]


def test_2_despues_goles_a_favor_entre_ellos() -> None:
    # A, B y C ganan uno cada uno; entre ellos, A hizo más goles.
    filas = tabla([A, B, C], [j(A, B, 3, 2), j(B, C, 1, 0), j(C, A, 2, 1)])
    assert orden(filas) == [A, B, C]  # GF entre ellos: A 4, B 3, C 2


def test_3_despues_menos_goles_en_contra() -> None:
    # Mismos puntos y goles a favor entre ellos; A recibió menos.
    filas = tabla([A, B, C], [j(A, B, 2, 1), j(B, C, 2, 0), j(C, A, 2, 0)])
    # GF: A 2, B 3, C 2 → B primero; entre A y C, GC: A 3, C 2 → C antes que A.
    assert orden(filas) == [B, C, A]


def test_4_despues_fair_play() -> None:
    filas = tabla(
        [A, B],
        [j(A, B, 1, 1)],
        tarjetas={A: Tarjetas(amarillas=2, rojas=0), B: Tarjetas(amarillas=0, rojas=1)},
    )
    assert orden(filas) == [B, A]  # B: 1 tarjeta; A: 2


def test_5_si_siguen_empatados_falta_el_sorteo() -> None:
    filas = tabla([A, B], [j(A, B, 1, 1)])
    assert all(f.falta_sorteo for f in filas)
    con_sorteo = tabla([A, B], [j(A, B, 1, 1)], sorteo={B: 1, A: 2})
    assert orden(con_sorteo) == [B, A] and not any(f.falta_sorteo for f in con_sorteo)


def test_p34_sin_partidos_entre_ellos_se_usan_todos_los_del_grupo() -> None:
    # Series cruzadas (H5): A y B (serie A) solo juegan contra C y D (serie B).
    partidos = [j(A, C, 2, 0), j(A, D, 0, 1), j(B, C, 1, 0), j(B, D, 0, 1)]
    filas = tabla([A, B], partidos)  # la tabla de la serie A
    assert orden(filas) == [A, B]  # 3 puntos cada uno; GF en el grupo: A 2, B 1
    assert not any(f.falta_sorteo for f in filas)


def test_orden_del_excel_de_2023_por_diferencia_de_gol() -> None:
    # A y B con 4 puntos y 0 a 0 entre ellos. Por el reglamento 2025 hace falta sorteo; con el
    # criterio del Excel de 2023 (diferencia de gol y goles a favor en el grupo), gana A.
    partidos = [j(A, B, 0, 0), j(A, C, 4, 3), j(B, C, 1, 0)]
    assert all(f.falta_sorteo for f in tabla([A, B, C], partidos)[:2])
    filas = tabla([A, B, C], partidos, criterio="diferencia_de_gol")
    assert orden(filas) == [A, B, C] and not any(f.falta_sorteo for f in filas)


def test_un_partido_sin_jugar_no_cuenta() -> None:
    filas = tabla([A, B, C], [j(A, B, 1, 0)])
    c = next(f for f in filas if f.equipo == C)
    assert (c.pj, c.puntos) == (0, 0)


def test_p26_mejor_tercero_por_puntos_por_partido_y_despues_diferencia() -> None:
    serie_a = tabla([A, B], [j(A, B, 1, 0), j(A, C, 0, 0)])
    serie_b = tabla([C, D], [j(C, D, 3, 0)])
    candidatos = [serie_a[1], serie_b[1]]  # B: 0 pts en 1 PJ; D: 0 pts en 1 PJ
    elegidos = mejores(candidatos)
    assert elegidos[0].equipo == B  # misma cantidad de puntos por partido; B: -1, D: -3
