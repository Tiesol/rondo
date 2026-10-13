"""T7.6: la fecha de nacimiento puede venir completa o solo con el año (pedido 2026, A3)."""

from datetime import date

import pytest

from dominio.nacimiento import Nacimiento, NacimientoInvalido, leer_nacimiento


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("12/03/2014", Nacimiento(2014, date(2014, 3, 12))),
        ("1/3/2014", Nacimiento(2014, date(2014, 3, 1))),
        ("12-03-2014", Nacimiento(2014, date(2014, 3, 12))),
        ("12.03.2014", Nacimiento(2014, date(2014, 3, 12))),
        ("2014-03-12", Nacimiento(2014, date(2014, 3, 12))),  # ISO, como el <input type=date>
        ("2014", Nacimiento(2014)),
        ("  2014 ", Nacimiento(2014)),
    ],
)
def test_lee_fecha_completa_o_solo_el_anio(texto: str, esperado: Nacimiento) -> None:
    assert leer_nacimiento(texto) == esperado


@pytest.mark.parametrize("texto", ["", "abc", "31/02/2014", "12/03/14", "14", "12/2014", "1850"])
def test_lo_que_no_se_entiende_es_un_error_con_ejemplos(texto: str) -> None:
    with pytest.raises(NacimientoInvalido, match="dd/mm/aaaa"):
        leer_nacimiento(texto)


def test_solo_el_anio_es_fecha_incompleta() -> None:
    assert not Nacimiento(2014).completa
    assert Nacimiento(2014, date(2014, 3, 12)).completa
    assert str(Nacimiento(2014)) == "2014"
    assert str(Nacimiento(2014, date(2014, 3, 12))) == "12/03/2014"


def test_el_anio_y_la_fecha_no_pueden_contradecirse() -> None:
    with pytest.raises(ValueError):
        Nacimiento(2015, date(2014, 3, 12))


def test_de_una_fecha() -> None:
    assert Nacimiento.de(date(2014, 3, 12)) == Nacimiento(2014, date(2014, 3, 12))
