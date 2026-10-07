"""T1.2: canchas compatibles (CAT-04) y canchas físicas que ocupa cada una (PRO-01)."""

from pathlib import Path

import pytest

from dominio.canchas import canchas_compatibles, canchas_fisicas
from dominio.config import cargar_config

CONFIG = cargar_config(Path(__file__).resolve().parents[2] / "datos/config/jmp_cup_2026.json")


@pytest.mark.parametrize(
    ("categoria", "nivel", "esperadas"),
    [
        ("Sub 5", "unico", ("C1A", "C1B")),
        ("Sub 6", "unico", ("C1A", "C1B")),  # F7, pero la regla por categoría manda (CAT-04)
        ("Sub 9", "inicial", ("C1", "C2")),
        ("Sub 10", "avanzado", ("C1",)),  # F8
        ("Sub 12", "avanzado", ("C3",)),  # F11
        ("Sub 15 Femenino", "unico", ("C1", "C2")),
    ],
)
def test_cat04_canchas_compatibles(categoria: str, nivel: str, esperadas: tuple[str, ...]) -> None:
    assert canchas_compatibles(CONFIG, categoria, nivel) == esperadas


def test_todas_las_categorias_nivel_de_2026_tienen_alguna_cancha() -> None:
    sin_cancha = [
        (c.nombre, n)
        for c in CONFIG.categorias
        for n in c.niveles
        if not canchas_compatibles(CONFIG, c.nombre, n)
    ]
    assert sin_cancha == []


def test_la_cancha_entera_ocupa_sus_mitades() -> None:
    fisicas = canchas_fisicas(CONFIG)
    assert fisicas["C1"] == frozenset({"C1A", "C1B"})
    assert fisicas["C1A"] == frozenset({"C1A"})
    assert fisicas["C2"] == frozenset({"C2"})
    assert set(fisicas) == {"C1", "C1A", "C1B", "C2", "C3"}


def test_un_nivel_que_la_categoria_no_tiene_es_un_error() -> None:
    with pytest.raises(KeyError, match="Sub 6 no tiene el nivel avanzado"):
        canchas_compatibles(CONFIG, "Sub 6", "avanzado")
