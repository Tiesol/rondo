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
