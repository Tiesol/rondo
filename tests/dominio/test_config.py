"""T1.1: configuración del torneo como datos (CAT-01, CAT-02, CAT-03)."""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from dominio.config import ConfigTorneo, cargar_config

CONFIG_2026 = Path(__file__).resolve().parents[2] / "datos" / "config" / "jmp_cup_2026.json"


@pytest.fixture
def config() -> ConfigTorneo:
    return cargar_config(CONFIG_2026)


def _crudo() -> dict[str, Any]:
    datos: dict[str, Any] = json.loads(CONFIG_2026.read_text())
    return datos


def test_la_configuracion_2026_tiene_13_categorias_y_23_categorias_nivel(
    config: ConfigTorneo,
) -> None:
    assert len(config.categorias) == 13
    assert sum(len(c.niveles) for c in config.categorias) == 23


@pytest.mark.parametrize(
    ("categoria", "anios"),
    [
        ("Sub 5", (2021,)),
        ("Sub 9", (2017,)),
        ("Sub 15 Femenino", (2011,)),
        ("Sub 17", (2009, 2010)),
    ],
)
def test_cat01_anios_de_nacimiento_en_2026(
    config: ConfigTorneo, categoria: str, anios: tuple[int, ...]
) -> None:
    assert config.categoria(categoria).anios_de_nacimiento(config.torneo.anio) == anios


# Tabla 4.4: turno = partido + 5 minutos de cambio.
TURNOS_4_4 = {
    ("Sub 5", "unico"): 40,
    ("Sub 6", "unico"): 40,
    **{(f"Sub {n}", nivel): 50 for n in (7, 8, 9, 10, 11) for nivel in ("inicial", "avanzado")},
    **{(f"Sub {n}", "inicial"): 50 for n in (12, 13, 14, 15, 17)},
    ("Sub 15 Femenino", "unico"): 50,
    ("Sub 12", "avanzado"): 60,
    ("Sub 13", "avanzado"): 60,
    ("Sub 14", "avanzado"): 70,
    ("Sub 15", "avanzado"): 70,
    ("Sub 17", "avanzado"): 70,
}


def test_cat03_los_turnos_coinciden_con_la_tabla_4_4(config: ConfigTorneo) -> None:
    obtenidos = {
        (c.nombre, nombre_nivel): config.minutos_turno(nivel)
        for c in config.categorias
        for nombre_nivel, nivel in c.niveles.items()
    }
    assert obtenidos == TURNOS_4_4


def test_cat03_el_partido_dura_dos_tiempos_mas_el_descanso(config: ConfigTorneo) -> None:
    nivel = config.categoria("Sub 14").niveles["avanzado"]
    assert config.minutos_partido(nivel) == 30 + 5 + 30


def test_rechaza_un_maximo_menor_que_el_minimo() -> None:
    datos = _crudo()
    datos["categorias"][2]["niveles"]["inicial"]["max"] = 5
    with pytest.raises(ValidationError, match="max"):
        ConfigTorneo.model_validate(datos)


def test_rechaza_un_nivel_desconocido() -> None:
    datos = _crudo()
    nivel = datos["categorias"][2]["niveles"].pop("inicial")
    datos["categorias"][2]["niveles"]["intermedio"] = nivel
    with pytest.raises(ValidationError, match="intermedio"):
        ConfigTorneo.model_validate(datos)


def test_rechaza_mezclar_nivel_unico_con_inicial_o_avanzado() -> None:
    datos = _crudo()
    datos["categorias"][0]["niveles"]["inicial"] = datos["categorias"][2]["niveles"]["inicial"]
    with pytest.raises(ValidationError, match="unico"):
        ConfigTorneo.model_validate(datos)


def test_rechaza_una_regla_con_tipo_incorrecto() -> None:
    datos = _crudo()
    datos["reglas"]["max_partidos_por_dia"] = "dos"
    with pytest.raises(ValidationError, match="max_partidos_por_dia"):
        ConfigTorneo.model_validate(datos)


def test_rechaza_una_compatibilidad_con_una_cancha_que_no_existe() -> None:
    datos = _crudo()
    datos["compatibilidad"]["por_modalidad"]["F7"] = ["C1", "C9"]
    with pytest.raises(ValidationError, match="C9"):
        ConfigTorneo.model_validate(datos)


def test_rechaza_una_regla_desconocida() -> None:
    datos = _crudo()
    datos["reglas"]["regla_inventada"] = True
    with pytest.raises(ValidationError, match="regla_inventada"):
        ConfigTorneo.model_validate(datos)
