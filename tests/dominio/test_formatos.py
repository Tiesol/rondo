"""FIX-01, FIX-02 y FIX-07: los formatos de 4.5 como datos (datos/config/formatos.json)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from dominio.formatos import FormatoFaltante, Formatos, cargar_formatos

ARCHIVO = Path(__file__).resolve().parents[2] / "datos" / "config" / "formatos.json"


@pytest.fixture(scope="module")
def formatos() -> Formatos:
    return cargar_formatos(ARCHIVO)


@pytest.mark.parametrize(
    ("equipos", "partidos"),
    [(2, 2), (3, 8), (4, 10), (5, 12), (6, 14), (7, 17), (8, 18), (9, 22), (10, 27)],
)
def test_fix_01_cada_formato_da_sus_partidos(
    formatos: Formatos, equipos: int, partidos: int
) -> None:
    assert formatos.para(equipos).total_de_partidos == partidos


def test_fix_02_con_dos_equipos_ida_y_vuelta_sin_eliminacion(formatos: Formatos) -> None:
    formato = formatos.para(2)
    assert formato.grupos.ida_y_vuelta
    assert formato.eliminacion == ()


@pytest.mark.parametrize("equipos", [0, 1, 11, 24])
def test_fix_02_sin_formato_es_un_error_que_cita_p27(formatos: Formatos, equipos: int) -> None:
    with pytest.raises(FormatoFaltante, match="P27"):
        formatos.para(equipos)


def test_fix_07_bronce_con_diez_equipos(formatos: Formatos) -> None:
    bronce = [p for p in formatos.para(10).eliminacion if p.copa == "bronce"]
    assert [(p.local.texto, p.visitante.texto) for p in bronce] == [("5.º A", "5.º B")]


def test_las_referencias_se_leen_en_espaniol(formatos: Formatos) -> None:
    final = next(p for p in formatos.para(6).eliminacion if p.clave == "plata_final")
    assert final.local.texto == "Ganador de la semi de Plata"
    assert final.visitante.texto == "Mejor perdedor de las semis de Oro"
    siete = {p.clave: p for p in formatos.para(7).eliminacion}
    assert siete["plata_final"].local.texto == "Mejor 3.º"
    assert siete["plata_semi"].local.texto == "El otro 3.º"


def test_las_series_suman_los_equipos(formatos: Formatos) -> None:
    for equipos in range(2, 11):
        formato = formatos.para(equipos)
        assert sum(formato.grupos.tamanios(equipos)) == equipos


def _con(cambio: dict[str, object]) -> dict[str, object]:
    datos: dict[str, object] = json.loads(ARCHIVO.read_text())
    formatos = datos["formatos"]
    assert isinstance(formatos, dict)
    formatos["4"] = formatos["4"] | cambio
    return datos


def test_una_referencia_a_un_partido_que_no_existe_falla() -> None:
    datos = _con({})
    formato = datos["formatos"]["4"]  # type: ignore[index]
    formato["eliminacion"][2]["local"] = {"ganador": "oro_semi_9"}
    with pytest.raises(ValidationError, match="oro_semi_9"):
        Formatos.model_validate(datos)


def test_una_serie_que_no_existe_falla() -> None:
    datos = _con({})
    formato = datos["formatos"]["8"]  # type: ignore[index]
    formato["eliminacion"][0]["local"] = {"puesto": 1, "serie": "C"}
    with pytest.raises(ValidationError, match="serie C"):
        Formatos.model_validate(datos)


def test_series_que_no_suman_los_equipos_fallan() -> None:
    datos = json.loads(ARCHIVO.read_text())
    datos["formatos"]["8"]["grupos"]["series"] = [4, 5]
    with pytest.raises(ValidationError, match="suman 9"):
        Formatos.model_validate(datos)
