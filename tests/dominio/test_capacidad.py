"""PRO-14: capacidad con flujo máximo, antes de programar."""

from dominio.capacidad import Demanda, calcular_capacidad

CANCHAS = {"C1": None, "C1A": "C1", "C1B": "C1", "C2": None, "C3": None}


def test_un_caso_chico_calculado_a_mano() -> None:
    demandas = [
        Demanda("Sub 6", minutos=400, canchas=frozenset({"C1A", "C1B"})),  # 200 de C1
        Demanda("Sub 9", minutos=1000, canchas=frozenset({"C1", "C2"})),
        Demanda("Sub 12", minutos=300, canchas=frozenset({"C3"})),
    ]
    grupos = calcular_capacidad(demandas, CANCHAS, {"C1": 600, "C2": 600, "C3": 200})
    por_canchas = {g.canchas: g for g in grupos}
    c1c2 = por_canchas[("C1", "C2")]
    assert (c1c2.pedido, c1c2.disponible, c1c2.ubicable) == (1200, 1200, 1200)
    assert c1c2.entra
    assert c1c2.categorias == ("Sub 6", "Sub 9")
    c3 = por_canchas[("C3",)]
    assert (c3.pedido, c3.disponible, c3.ubicable) == (300, 200, 200)
    assert not c3.entra


def test_los_totales_alcanzan_pero_la_compatibilidad_no() -> None:
    demandas = [
        Demanda("Solo C1", minutos=700, canchas=frozenset({"C1"})),
        Demanda("C1 o C2", minutos=300, canchas=frozenset({"C1", "C2"})),
    ]
    (grupo,) = calcular_capacidad(demandas, CANCHAS, {"C1": 600, "C2": 600, "C3": 0})
    assert (grupo.pedido, grupo.disponible) == (1000, 1200)
    assert grupo.ubicable == 900
    assert not grupo.entra
    assert grupo.faltan == 100


def test_una_mitad_ocupa_media_cancha() -> None:
    (grupo,) = calcular_capacidad(
        [Demanda("Sub 5", minutos=500, canchas=frozenset({"C1A", "C1B"}))],
        CANCHAS,
        {"C1": 300},
    )
    assert (grupo.pedido, grupo.disponible, grupo.entra) == (250, 300, True)


def test_sin_demanda_no_hay_grupos() -> None:
    assert calcular_capacidad([], CANCHAS, {"C1": 300}) == []


def test_una_categoria_sin_canchas_compatibles_no_entra() -> None:
    (grupo,) = calcular_capacidad(
        [Demanda("Sub 17", minutos=70, canchas=frozenset())], CANCHAS, {"C1": 300}
    )
    assert grupo.canchas == ()
    assert not grupo.entra
