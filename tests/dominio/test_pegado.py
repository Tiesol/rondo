"""T7.7: leer las filas que la organización pega desde Excel, Word o un PDF pasado a Excel.

Las cinco formas de lista de 2023 (CONTEXTO 6.5), recreadas con datos inventados.
"""

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dominio.nacimiento import Nacimiento
from dominio.pegado import (
    Analisis,
    FilaLeida,
    analizar,
    leer_fecha,
    leer_filas,
    leer_rol,
    separar_nombre,
)

ROLES = ("entrenador", "asistente", "delegado")


def leer(texto: str) -> tuple[Analisis, list[FilaLeida]]:
    analisis = analizar(texto, ROLES)
    return analisis, leer_filas(analisis, ROLES)


# ---------- Las cinco formas de 2023 ----------


def test_plantilla_jmp_en_excel() -> None:
    texto = (
        "Nº\tNOMBRES\tAPELLIDOS\tFECHA DE NACIMIENTO\tNº DOCUMENTO\tDORSAL\n"
        "1\tJuan Carlos\tPérez Gómez\t14/03/2017\t1234567 SC\t10\n"
        "2\tAna\tRoca Vaca\t02/11/2017\t7654321-1E LP\t\n"
        "3\tLuis\tMendoza Paz\t2017\t\t7\n"
    )
    analisis, filas = leer(texto)
    assert analisis.encabezado is not None
    assert analisis.columnas == [
        "ignorar",
        "nombres",
        "apellidos",
        "nacimiento",
        "documento",
        "dorsal",
    ]
    assert filas[0] == FilaLeida(
        1, "Juan Carlos", "Pérez Gómez", Nacimiento.de(date(2017, 3, 14)), "1234567 SC", 10
    )
    assert filas[1].dorsal is None and filas[1].documento == "7654321-1E LP"
    assert filas[2].nacimiento == Nacimiento(2017)


def test_plantilla_reordenada() -> None:
    texto = (
        "APELLIDOS\tNOMBRES\tCI\tFECHA NAC.\tDORSAL\nPérez Gómez\tJuan\t1234567\t14/03/2017\t9\n"
    )
    analisis, filas = leer(texto)
    assert analisis.columnas == ["apellidos", "nombres", "documento", "nacimiento", "dorsal"]
    assert (filas[0].nombres, filas[0].apellidos, filas[0].dorsal) == ("Juan", "Pérez Gómez", 9)


def test_pdf_pasado_a_excel_sin_encabezado_y_en_mm_dd() -> None:
    texto = (
        "1\tJUAN CARLOS PEREZ GOMEZ\t03/14/2017\t1234567\n"
        "2\tANA ROCA VACA\t11/02/2017\t7654321\n"
        "3\tLUIS MENDOZA PAZ\t05/20/2017\t1111111\n"
    )
    analisis, filas = leer(texto)
    assert analisis.encabezado is None
    assert analisis.columnas == ["ignorar", "nombre_completo", "nacimiento", "documento"]
    assert analisis.orden_fechas == "mda"
    assert analisis.aviso_fechas  # se avisa que la lista entera venía en mm/dd/aaaa
    assert (filas[0].nombres, filas[0].apellidos) == ("JUAN CARLOS", "PEREZ GOMEZ")
    assert filas[1].nacimiento == Nacimiento.de(date(2017, 11, 2))  # corregida como mm/dd


def test_lista_propia_con_rude_y_mes_en_letras() -> None:
    texto = (
        "N°\tRUDE\tAPELLIDOS Y NOMBRES\tF. NACIMIENTO\tC.I.\n"
        "1\t80123456789012\tPÉREZ GÓMEZ, JUAN CARLOS\t12 de marzo 2014\t1234567 SC\n"
        "2\t80123456789013\tROCA VACA ANA\t3 de Noviembre de 2014\t\n"
    )
    analisis, filas = leer(texto)
    assert analisis.columnas == [
        "ignorar",
        "ignorar",
        "apellidos_nombres",
        "nacimiento",
        "documento",
    ]
    assert (filas[0].nombres, filas[0].apellidos) == ("JUAN CARLOS", "PÉREZ GÓMEZ")
    assert filas[0].nacimiento == Nacimiento.de(date(2014, 3, 12))
    assert (filas[1].nombres, filas[1].apellidos) == ("ANA", "ROCA VACA")
    assert filas[1].nacimiento == Nacimiento.de(date(2014, 11, 3))


def test_tabla_de_word_con_solo_el_anio() -> None:
    texto = (
        "Nº\tNOMBRES\tAPELLIDOS\tAÑO NACIMIENTO\tNº DOCUMENTO\n"
        "1 \t Juan \t Pérez Gómez \t 2014 \t 1234567 \n"
        "\t\t\t\t\n"
        "2\tAna\tRoca\t2014\t\n"
    )
    analisis, filas = leer(texto)
    assert analisis.columnas[3] == "nacimiento"
    assert len(filas) == 2  # la fila vacía de Word no cuenta
    assert filas[0] == FilaLeida(1, "Juan", "Pérez Gómez", Nacimiento(2014), "1234567", None)


# ---------- Cuerpo técnico ----------


def test_cuerpo_tecnico_con_roles_escritos_de_varias_formas() -> None:
    texto = (
        "Nº\tNOMBRES\tAPELLIDOS\tFUNCION\tNº TELEFONO\n"
        "1\tCarlos\tSuárez Rojas\tD.T\t70000000\n"
        "2\tMario\tVaca Díez\tA.C\t70000001\n"
        "3\tRosa\tPaz Soria\tDelegada\t70000002\n"
    )
    analisis, filas = leer(texto)
    assert analisis.columnas == ["ignorar", "nombres", "apellidos", "rol", "ignorar"]
    assert [f.rol for f in filas] == ["entrenador", "asistente", "delegado"]


@pytest.mark.parametrize(
    ("texto", "rol"),
    [
        ("DT", "entrenador"),
        ("D.T.", "entrenador"),
        ("Director técnico", "entrenador"),
        ("Entrenador", "entrenador"),
        ("profe", "entrenador"),
        ("Asistente técnico", "asistente"),
        ("A.T.", "asistente"),
        ("ayudante", "asistente"),
        ("DELEGADO", "delegado"),
        ("Utilero", None),
        ("", None),
    ],
)
def test_leer_rol(texto: str, rol: str | None) -> None:
    assert leer_rol(texto, ROLES) == rol


def test_un_rol_que_no_esta_en_la_configuracion_no_se_propone() -> None:
    assert leer_rol("Delegado", ("entrenador", "asistente")) is None


# ---------- Fechas ----------


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("14/03/2017", Nacimiento.de(date(2017, 3, 14))),
        ("14/03/17", Nacimiento.de(date(2017, 3, 14))),  # año corto de Excel
        ("2017-03-14", Nacimiento.de(date(2017, 3, 14))),
        ("2017-03-14 00:00:00", Nacimiento.de(date(2017, 3, 14))),  # fecha de Excel con hora
        ("42808", Nacimiento.de(date(2017, 3, 14))),  # número de fecha de Excel
        ("12 de marzo 2014", Nacimiento.de(date(2014, 3, 12))),
        ("12 de marzo de 2014", Nacimiento.de(date(2014, 3, 12))),
        ("12-mar-2014", Nacimiento.de(date(2014, 3, 12))),
        ("12 Septiembre 2014", Nacimiento.de(date(2014, 9, 12))),
        ("12 setiembre 2014", Nacimiento.de(date(2014, 9, 12))),
        ("2014", Nacimiento(2014)),
    ],
)
def test_leer_fecha(texto: str, esperado: Nacimiento) -> None:
    assert leer_fecha(texto, "dma") == esperado


def test_leer_fecha_en_mm_dd() -> None:
    assert leer_fecha("03/14/2017", "mda") == Nacimiento.de(date(2017, 3, 14))


def test_lista_con_fechas_ambiguas_queda_en_dd_mm_sin_aviso() -> None:
    analisis, filas = leer("Juan\tPérez\t03/04/2017\nAna\tRoca\t05/06/2017\n")
    assert analisis.orden_fechas == "dma"
    assert analisis.aviso_fechas == ""
    assert filas[0].nacimiento == Nacimiento.de(date(2017, 4, 3))


def test_una_fecha_que_no_se_entiende_queda_como_error_de_la_fila() -> None:
    _, filas = leer("Juan\tPérez\t31/02/2017\nAna\tRoca\t05/06/2017\n")
    assert filas[0].nacimiento is None
    assert filas[0].errores and "31/02/2017" in filas[0].errores[0]
    assert filas[1].errores == ()


@given(st.dates(min_value=date(1950, 1, 1), max_value=date(2025, 12, 31)))
def test_propiedad_cualquier_fecha_se_lee_en_sus_formas(fecha: date) -> None:
    esperado = Nacimiento.de(fecha)
    assert leer_fecha(f"{fecha:%d/%m/%Y}", "dma") == esperado
    assert leer_fecha(f"{fecha:%m/%d/%Y}", "mda") == esperado
    assert leer_fecha(fecha.isoformat(), "dma") == esperado
    excel = (fecha - date(1899, 12, 30)).days
    assert leer_fecha(str(excel), "dma") == esperado


# ---------- Nombres ----------


@pytest.mark.parametrize(
    ("texto", "orden", "esperado"),
    [
        ("Juan Carlos Pérez Gómez", "nombres_primero", ("Juan Carlos", "Pérez Gómez")),
        ("Ana Roca Vaca", "nombres_primero", ("Ana", "Roca Vaca")),
        ("Ana Roca", "nombres_primero", ("Ana", "Roca")),
        ("Pérez Gómez Juan Carlos", "apellidos_primero", ("Juan Carlos", "Pérez Gómez")),
        ("PÉREZ GÓMEZ, JUAN CARLOS", "apellidos_primero", ("JUAN CARLOS", "PÉREZ GÓMEZ")),
        ("  Juan   Pérez  ", "nombres_primero", ("Juan", "Pérez")),
        ("Juan", "nombres_primero", ("Juan", "")),
    ],
)
def test_separar_nombre(texto: str, orden: str, esperado: tuple[str, str]) -> None:
    assert separar_nombre(texto, orden) == esperado  # type: ignore[arg-type]


@given(
    st.lists(st.from_regex(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]{2,10}", fullmatch=True), min_size=3, max_size=5)
)
def test_propiedad_separar_no_pierde_palabras(palabras: list[str]) -> None:
    nombres, apellidos = separar_nombre(" ".join(palabras), "nombres_primero")
    assert f"{nombres} {apellidos}".split() == palabras
    assert len(apellidos.split()) == 2


# ---------- Columnas a mano ----------


def test_la_organizacion_corrige_las_columnas() -> None:
    analisis = analizar("Juan\tPérez Gómez\t2017\n", ROLES)
    corregido = analisis.con_columnas(["apellidos", "nombres", "nacimiento"])
    fila = leer_filas(corregido, ROLES)[0]
    assert (fila.nombres, fila.apellidos) == ("Pérez Gómez", "Juan")


def test_dorsal_que_no_es_numero_es_error_de_la_fila() -> None:
    analisis = analizar("Juan\tPérez\t2017\tdiez\n", ROLES).con_columnas(
        ["nombres", "apellidos", "nacimiento", "dorsal"]
    )
    fila = leer_filas(analisis, ROLES)[0]
    assert fila.dorsal is None and any("diez" in e for e in fila.errores)


def test_texto_vacio_no_tiene_filas() -> None:
    analisis, filas = leer("  \n\n")
    assert analisis.filas == [] and filas == []
