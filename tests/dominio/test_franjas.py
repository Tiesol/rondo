"""T1.2: las franjas por día de la semana se vuelven franjas con fecha y hora."""

from datetime import UTC, datetime
from pathlib import Path

from dominio.config import cargar_config
from dominio.franjas import franjas_del_torneo

CONFIG = cargar_config(Path(__file__).resolve().parents[2] / "datos/config/jmp_cup_2026.json")


def test_2026_tiene_15_franjas_en_cinco_fines_de_semana() -> None:
    franjas = franjas_del_torneo(CONFIG)
    assert len(franjas) == 15
    dias = [f.inicio.strftime("%a") for f in franjas]
    assert dias == ["Fri", "Sat", "Sun"] * 5


def test_la_primera_es_el_viernes_23_de_16_a_20_hora_de_bolivia() -> None:
    primera = franjas_del_torneo(CONFIG)[0]
    assert primera.inicio == datetime(2026, 10, 23, 20, 0, tzinfo=UTC)
    assert primera.fin == datetime(2026, 10, 24, 0, 0, tzinfo=UTC)


def test_la_ultima_es_el_domingo_22_de_noviembre_de_8_a_16() -> None:
    ultima = franjas_del_torneo(CONFIG)[-1]
    local = ultima.inicio.astimezone(ultima.inicio.tzinfo)
    assert (local.date().isoformat(), ultima.duracion_min) == ("2026-11-22", 8 * 60)
