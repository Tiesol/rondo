"""T1.2: las franjas por día de la semana se vuelven franjas con fecha y hora."""

from datetime import UTC, datetime
from pathlib import Path

from dominio.config import cargar_config
from dominio.franjas import franjas_del_torneo

CONFIG = cargar_config(Path(__file__).resolve().parents[2] / "datos/config/jmp_cup_2026.json")


def test_2026_tiene_11_franjas_en_cuatro_fines_de_semana() -> None:
    # Convocatoria 2026: del sábado 24/10 al domingo 15/11; el viernes 23 no se juega.
    franjas = franjas_del_torneo(CONFIG)
    assert len(franjas) == 11
    dias = [f.inicio.strftime("%a") for f in franjas]
    assert dias == ["Sat", "Sun"] + ["Fri", "Sat", "Sun"] * 3


def test_la_primera_es_el_sabado_24_de_8_a_16_hora_de_bolivia() -> None:
    primera = franjas_del_torneo(CONFIG)[0]
    assert primera.inicio == datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
    assert primera.fin == datetime(2026, 10, 24, 20, 0, tzinfo=UTC)


def test_la_ultima_es_el_domingo_15_de_noviembre_de_8_a_16() -> None:
    ultima = franjas_del_torneo(CONFIG)[-1]
    local = ultima.inicio.astimezone(ultima.inicio.tzinfo)
    assert (local.date().isoformat(), ultima.duracion_min) == ("2026-11-15", 8 * 60)


def test_proximo_dia_de_la_semana() -> None:
    from datetime import date

    from dominio.franjas import proximo

    assert proximo(date(2026, 10, 31), "jueves") == date(2026, 11, 5)  # sábado → jueves
    assert proximo(date(2026, 11, 5), "jueves") == date(2026, 11, 5)  # ya es jueves
    assert proximo(date(2026, 11, 6), "jueves") == date(2026, 11, 12)  # viernes → jueves
