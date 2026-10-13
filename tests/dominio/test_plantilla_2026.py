"""T7.4: la plantilla 2026 según la convocatoria (CONVOCATORIA_2026_PARA_RONDO.md y el pedido)."""

from datetime import date, datetime
from pathlib import Path

import pytest

from dominio.canchas import canchas_compatibles
from dominio.config import ConfigTorneo, Reglas, cargar_config
from dominio.franjas import franjas_del_torneo
from dominio.inscripcion import validar_cierre

CONFIG_2026 = Path(__file__).resolve().parents[2] / "datos" / "config" / "jmp_cup_2026.json"


@pytest.fixture
def config() -> ConfigTorneo:
    return cargar_config(CONFIG_2026)


def _nivel(config: ConfigTorneo, categoria: str, nivel: str) -> str:
    return next(c for c in config.categorias if c.nombre == categoria).niveles[nivel].modalidad  # type: ignore[index]


def test_fechas_del_24_10_al_15_11_con_11_dias_de_juego(config: ConfigTorneo) -> None:
    assert (config.torneo.inicio, config.torneo.fin) == (date(2026, 10, 24), date(2026, 11, 15))
    dias = sorted({f.inicio.date() for f in franjas_del_torneo(config)})
    assert len(dias) == 11
    assert date(2026, 10, 23) not in dias  # el viernes 23 no se juega
    assert date(2026, 10, 30) in dias and date(2026, 11, 13) in dias


def test_eliminacion_en_el_4_fin_de_semana_y_cierre_el_21_10_a_las_12(
    config: ConfigTorneo,
) -> None:
    assert config.reglas.eliminacion_desde_fin_de_semana == 4
    assert config.reglas.cierre_inscripcion == datetime(2026, 10, 21, 12, 0)


def test_sub_5_y_sub_6_juegan_futbol_6_en_media_cancha_1(config: ConfigTorneo) -> None:
    # P63: por defecto, en C1A y C1B, como en 2023.
    for categoria in ("Sub 5", "Sub 6"):
        assert _nivel(config, categoria, "unico") == "F6"
        assert set(canchas_compatibles(config, categoria, "unico")) == {"C1A", "C1B"}


def test_sub_10_y_sub_11_avanzado_siguen_en_f8(config: ConfigTorneo) -> None:
    # P60: F8 por defecto; si la respuesta es F11, es un cambio de configuración.
    assert _nivel(config, "Sub 10", "avanzado") == "F8"
    assert _nivel(config, "Sub 11", "avanzado") == "F8"


def test_sub_15_femenino_queda_disponible_pero_destildada(config: ConfigTorneo) -> None:
    # P61: no se juega por defecto, pero se puede tildar en el asistente.
    femenino = next(c for c in config.categorias if c.nombre == "Sub 15 Femenino")
    assert femenino.tildada_en_asistente is False
    assert all(c.tildada_en_asistente for c in config.categorias if c is not femenino)


def test_para_reprogramar_se_propone_el_jueves(config: ConfigTorneo) -> None:
    assert config.reglas.dia_para_reprogramar == "jueves"


# ---------- INS-11 con hora ----------


def test_el_cierre_es_a_las_12_la_mesa_carga_hasta_ese_minuto() -> None:
    reglas = Reglas(cierre_inscripcion=datetime(2026, 10, 21, 12, 0))
    assert validar_cierre(datetime(2026, 10, 21, 11, 59), reglas, es_organizacion=False) == []
    tarde = validar_cierre(datetime(2026, 10, 21, 12, 1), reglas, es_organizacion=False)
    assert [h.regla for h in tarde] == ["INS-11"]
    assert "12:00" in tarde[0].mensaje
    assert validar_cierre(datetime(2026, 10, 21, 12, 1), reglas, es_organizacion=True) == []


def test_un_cierre_guardado_solo_con_fecha_cierra_al_final_del_dia() -> None:
    # Los torneos de antes guardaban solo la fecha: ese día todavía se podía cargar.
    reglas = Reglas.model_validate({"cierre_inscripcion": "2026-10-20"})
    assert validar_cierre(datetime(2026, 10, 20, 23, 0), reglas, es_organizacion=False) == []
    assert validar_cierre(datetime(2026, 10, 21, 0, 1), reglas, es_organizacion=False) != []


def test_respuestas_del_organizador_en_el_calendario(config: ConfigTorneo) -> None:
    # P35: todas las canchas están en el mismo predio; P19: el orden de las fechas es flexible.
    assert config.reglas.profe_minutos_cambio_de_cancha == 0
    assert config.reglas.orden_de_fechas == "blanda"
