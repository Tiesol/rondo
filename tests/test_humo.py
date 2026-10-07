import sys


def test_el_entorno_usa_python_3_14() -> None:
    assert sys.version_info[:2] == (3, 14)
