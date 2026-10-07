"""INS-04: el CI se normaliza para comparar (número, complemento y "E-"). Datos inventados."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dominio.documentos import SIGLAS, Documento, DocumentoInvalido, normalizar_documento


@pytest.mark.parametrize(
    ("texto", "tipo", "numero", "complemento", "sigla", "clave"),
    [
        ("1234567 SC", "ci", "1234567", "", "SC", "1234567"),
        ("1234567-1E", "ci", "1234567", "1E", "", "1234567-1E"),
        ("E-1234567", "ci_extranjero", "1234567", "", "", "E-1234567"),
        ("1.234.567 lp", "ci", "1234567", "", "LP", "1234567"),
        ("1234567SC", "ci", "1234567", "", "SC", "1234567"),
        ("AB123456", "pasaporte", "AB123456", "", "", "P-AB123456"),
        ("  7654321-2a cb ", "ci", "7654321", "2A", "CB", "7654321-2A"),
        ("1234567-SC", "ci", "1234567", "", "SC", "1234567"),
        ("1234567 S.C.", "ci", "1234567", "", "SC", "1234567"),
        ("e1234567", "ci_extranjero", "1234567", "", "", "E-1234567"),
    ],
)
def test_ins_04_formatos_conocidos(
    texto: str, tipo: str, numero: str, complemento: str, sigla: str, clave: str
) -> None:
    documento = normalizar_documento(texto)
    assert documento == Documento(tipo, numero, complemento, sigla)  # type: ignore[arg-type]
    assert documento.clave == clave


def test_ins_04_la_sigla_no_cambia_la_clave_y_el_complemento_si() -> None:
    def clave(texto: str) -> str:
        documento = normalizar_documento(texto)
        assert documento is not None
        return documento.clave

    assert clave("1234567 SC") == clave("1234567 LP") == clave("1234567")
    assert clave("1234567") != clave("1234567-1E")
    assert clave("1234567") != clave("E-1234567")


@pytest.mark.parametrize("texto", ["", "   ", "S/N", "pendiente", "-"])
def test_ins_04_sin_digitos_es_sin_documento(texto: str) -> None:
    assert normalizar_documento(texto) is None


@pytest.mark.parametrize("texto", ["12#45", "123", "1234567 XX", "1234567-ABC", "12 34 ab 56 cd"])
def test_ins_04_lo_que_no_se_reconoce_da_un_error_claro(texto: str) -> None:
    with pytest.raises(DocumentoInvalido, match="Ejemplos válidos"):
        normalizar_documento(texto)


def test_ins_04_se_muestra_ordenado() -> None:
    documento = normalizar_documento("1.234.567-1e  sc")
    assert documento is not None
    assert documento.texto == "1234567-1E SC"


@given(
    numero=st.integers(min_value=1000, max_value=99_999_999),
    sigla=st.sampled_from(["", *SIGLAS]),
    separador=st.sampled_from(["", " ", "-", "  "]),
    minusculas=st.booleans(),
)
def test_ins_04_las_formas_de_escribir_un_mismo_ci_dan_la_misma_clave(
    numero: int, sigla: str, separador: str, minusculas: bool
) -> None:
    con_puntos = f"{numero:,}".replace(",", ".")
    texto = f"{con_puntos}{separador if sigla else ''}{sigla}"
    documento = normalizar_documento(texto.lower() if minusculas else texto)
    assert documento is not None
    assert documento.clave == str(numero)
