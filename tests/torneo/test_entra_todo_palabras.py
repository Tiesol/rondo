"""T13.31: "¿Entra todo?" en palabras: "C3: 14 partidos (16 h) de 88 h disponibles. Entran
unos 60 partidos más de 70 min.", con las categorías que juegan ahí."""

from dominio.capacidad import GrupoDeCanchas
from torneo.views.programar import en_palabras


def test_dice_partidos_horas_y_cuantos_mas_entran() -> None:
    grupo = GrupoDeCanchas(
        ("C3",), ("Sub 14 Avanzado",), pedido=14 * 70, disponible=88 * 60, ubicable=88 * 60
    )
    texto = en_palabras(grupo, partidos=14, turno=70)
    assert texto == (
        "C3: 14 partidos (16 h) de 88 h disponibles. Entran unos 61 partidos más de 70 min."
    )


def test_si_no_entra_no_promete_mas() -> None:
    grupo = GrupoDeCanchas(
        ("C3",), ("Sub 10 Avanzado",), pedido=6000, disponible=5000, ubicable=5000
    )
    texto = en_palabras(grupo, partidos=80, turno=75)
    assert texto == "C3: 80 partidos (100 h) de 83 h disponibles."


def test_t13_34_cuenta_lo_libre_con_el_grupo_que_da_el_flujo() -> None:
    """La prueba de Sebastian: 130 partidos (93 h) de 168 h decía "Entran unos 0 partidos más".
    El flujo nunca ubica más de lo pedido: lo que entra sale de lo libre."""
    from dominio.capacidad import Demanda, calcular_capacidad

    turno = 50
    pedido = 93 * 60  # 130 partidos que suman 93 h
    [grupo] = calcular_capacidad(
        [Demanda("Sub 9", pedido, frozenset({"C1", "C2"}))],
        {"C1": None, "C2": None},
        {"C1": 84 * 60, "C2": 84 * 60},
    )
    assert grupo.ubicable == grupo.pedido  # nunca más de lo pedido

    texto = en_palabras(grupo, partidos=130, turno=turno)

    assert texto == (
        "C1 y C2: 130 partidos (93 h) de 168 h disponibles. Entran unos 90 partidos más de 50 min."
    )
