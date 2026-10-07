"""INS-02 a INS-11: validaciones de inscripción, sin base de datos. Datos inventados."""

from dataclasses import replace
from datetime import date

import pytest

from dominio.config import CuerpoTecnico, Reglas
from dominio.documentos import normalizar_documento
from dominio.inscripcion import (
    AltaDeJugador,
    AltaDeProfe,
    CategoriaDelEquipo,
    EquipoRef,
    Hallazgo,
    Participacion,
    validar_alta_de_jugador,
    validar_alta_de_profe,
    validar_cierre,
)

RIVER_SUB9 = EquipoRef(1, "River Plate", "Sub 9", "Sub 9 Avanzado")
RIVER_SUB11 = EquipoRef(2, "River Plate", "Sub 11", "Sub 11 Avanzado")
RIVER_SUB9_INI = EquipoRef(3, "River Plate", "Sub 9", "Sub 9 Inicial")
LEONES_SUB11 = EquipoRef(4, "Leones", "Sub 11", "Sub 11 Avanzado")
SUB9 = CategoriaDelEquipo(edad=9, anios_nacimiento=1, min_jugadores=12, max_jugadores=14)
SUB17 = CategoriaDelEquipo(edad=17, anios_nacimiento=2, min_jugadores=18, max_jugadores=22)


def alta(**cambios: object) -> AltaDeJugador:
    base = AltaDeJugador(
        equipo=RIVER_SUB9,
        categoria=SUB9,
        anio_torneo=2026,
        nacimiento=date(2017, 3, 14),
        documento=normalizar_documento("1234567 SC"),
        dorsal=10,
        jugadores_en_el_equipo=12,
        dorsales_en_el_equipo=frozenset({1, 2, 3}),
        otras_participaciones=(),
    )
    return replace(base, **cambios)  # type: ignore[arg-type]


def reglas(**cambios: object) -> Reglas:
    return Reglas.model_validate(Reglas().model_dump() | cambios)


def de_la_regla(hallazgos: list[Hallazgo], regla: str) -> list[Hallazgo]:
    return [h for h in hallazgos if h.regla == regla]


def niveles(hallazgos: list[Hallazgo], regla: str) -> list[str]:
    return [h.nivel for h in de_la_regla(hallazgos, regla)]


def test_un_jugador_que_cumple_todo_no_tiene_hallazgos() -> None:
    assert validar_alta_de_jugador(alta(), Reglas()) == []


# ---------- INS-02: edad ----------


def test_ins_02_un_jugador_mayor_que_su_categoria_es_un_error() -> None:
    hallazgos = validar_alta_de_jugador(alta(nacimiento=date(2016, 12, 31)), Reglas())
    assert niveles(hallazgos, "INS-02") == ["error"]
    assert "2016" in de_la_regla(hallazgos, "INS-02")[0].mensaje


def test_ins_02_mayor_es_error_aunque_se_permita_jugar_en_categoria_mayor() -> None:
    hallazgos = validar_alta_de_jugador(
        alta(nacimiento=date(2015, 1, 1)), reglas(jugar_en_categoria_mayor=True)
    )
    assert niveles(hallazgos, "INS-02") == ["error"]


def test_ins_02_uno_menor_se_acepta_sin_aviso_hasta_el_limite() -> None:
    hallazgos = validar_alta_de_jugador(alta(nacimiento=date(2019, 5, 1)), Reglas())
    assert de_la_regla(hallazgos, "INS-02") == []


def test_ins_02_uno_menor_por_mas_de_aviso_anios_menor_da_aviso() -> None:
    hallazgos = validar_alta_de_jugador(alta(nacimiento=date(2020, 5, 1)), Reglas())
    assert niveles(hallazgos, "INS-02") == ["aviso"]
    assert "3 años menor" in de_la_regla(hallazgos, "INS-02")[0].mensaje


def test_ins_02_uno_menor_es_error_si_no_se_permite_jugar_en_categoria_mayor() -> None:
    hallazgos = validar_alta_de_jugador(
        alta(nacimiento=date(2018, 5, 1)), reglas(jugar_en_categoria_mayor=False)
    )
    assert niveles(hallazgos, "INS-02") == ["error"]


@pytest.mark.parametrize("anio", [2009, 2010])
def test_ins_02_sub_17_acepta_los_dos_anios(anio: int) -> None:
    hallazgos = validar_alta_de_jugador(
        alta(categoria=SUB17, nacimiento=date(anio, 6, 1), jugadores_en_el_equipo=18), Reglas()
    )
    assert de_la_regla(hallazgos, "INS-02") == []


def test_ins_02_sin_fecha_de_nacimiento_es_un_error() -> None:
    assert niveles(validar_alta_de_jugador(alta(nacimiento=None), Reglas()), "INS-02") == ["error"]


# ---------- INS-03: cantidad ----------


def test_ins_03_no_se_pasa_del_maximo() -> None:
    hallazgos = validar_alta_de_jugador(alta(jugadores_en_el_equipo=14), Reglas())
    assert niveles(hallazgos, "INS-03") == ["error"]


def test_ins_03_el_ultimo_lugar_entra() -> None:
    assert (
        de_la_regla(validar_alta_de_jugador(alta(jugadores_en_el_equipo=13), Reglas()), "INS-03")
        == []
    )


def test_ins_03_por_debajo_del_minimo_hay_aviso_con_lo_que_falta() -> None:
    hallazgos = validar_alta_de_jugador(alta(jugadores_en_el_equipo=5), Reglas())
    assert niveles(hallazgos, "INS-03") == ["aviso"]
    assert "faltan 6" in de_la_regla(hallazgos, "INS-03")[0].mensaje.lower()


# ---------- INS-05 a INS-07: otros equipos ----------


def test_ins_05_mismo_club_otra_categoria_es_aviso() -> None:
    otras = (Participacion(RIVER_SUB11, "jugador"),)
    hallazgos = validar_alta_de_jugador(alta(otras_participaciones=otras), Reglas())
    assert niveles(hallazgos, "INS-05") == ["aviso"]
    assert "Sub 11 Avanzado de River Plate" in de_la_regla(hallazgos, "INS-05")[0].mensaje


def test_ins_05_otro_club_es_error() -> None:
    otras = (Participacion(LEONES_SUB11, "jugador"),)
    assert niveles(
        validar_alta_de_jugador(alta(otras_participaciones=otras), Reglas()), "INS-05"
    ) == ["error"]


def test_ins_05_misma_categoria_otro_nivel_es_error() -> None:
    otras = (Participacion(RIVER_SUB9_INI, "jugador"),)
    assert niveles(
        validar_alta_de_jugador(alta(otras_participaciones=otras), Reglas()), "INS-05"
    ) == ["error"]


def test_ins_05_con_la_regla_nunca_es_error_siempre() -> None:
    otras = (Participacion(RIVER_SUB11, "jugador"),)
    hallazgos = validar_alta_de_jugador(
        alta(otras_participaciones=otras), reglas(jugador_en_dos_equipos="nunca")
    )
    assert niveles(hallazgos, "INS-05") == ["error"]


def test_ins_05_ya_esta_en_este_equipo_es_error() -> None:
    otras = (Participacion(RIVER_SUB9, "jugador"),)
    assert niveles(
        validar_alta_de_jugador(alta(otras_participaciones=otras), Reglas()), "INS-05"
    ) == ["error"]


def profe(**cambios: object) -> AltaDeProfe:
    base = AltaDeProfe(
        equipo=RIVER_SUB9,
        rol="asistente",
        documento=normalizar_documento("7654321 LP"),
        roles_en_el_equipo=("entrenador",),
        otras_participaciones=(),
    )
    return replace(base, **cambios)  # type: ignore[arg-type]


def test_ins_06_un_profe_en_varios_equipos_de_cualquier_club_se_permite() -> None:
    otras = (Participacion(LEONES_SUB11, "profe"), Participacion(RIVER_SUB11, "profe"))
    hallazgos = validar_alta_de_profe(profe(otras_participaciones=otras), CuerpoTecnico(), Reglas())
    assert niveles(hallazgos, "INS-06") == ["aviso"]
    assert "no juegan a la vez" in de_la_regla(hallazgos, "INS-06")[0].mensaje


def test_ins_07_jugador_en_un_equipo_y_profe_en_otro_es_aviso() -> None:
    otras = (Participacion(LEONES_SUB11, "jugador"),)
    hallazgos = validar_alta_de_profe(profe(otras_participaciones=otras), CuerpoTecnico(), Reglas())
    assert niveles(hallazgos, "INS-07") == ["aviso"]


def test_ins_07_si_la_regla_no_lo_permite_es_error() -> None:
    otras = (Participacion(LEONES_SUB11, "profe"),)
    hallazgos = validar_alta_de_jugador(
        alta(otras_participaciones=otras), reglas(jugador_y_profe=False)
    )
    assert niveles(hallazgos, "INS-07") == ["error"]


# ---------- INS-08: cuerpo técnico ----------


def test_ins_08_hasta_tres_en_el_cuerpo_tecnico() -> None:
    lleno = profe(roles_en_el_equipo=("entrenador", "asistente", "delegado"))
    assert niveles(validar_alta_de_profe(lleno, CuerpoTecnico(), Reglas()), "INS-08") == ["error"]


def test_ins_08_un_solo_entrenador() -> None:
    otro = profe(rol="entrenador")
    assert niveles(validar_alta_de_profe(otro, CuerpoTecnico(), Reglas()), "INS-08") == ["error"]


def test_ins_08_rol_desconocido() -> None:
    raro = profe(rol="utilero")
    assert niveles(validar_alta_de_profe(raro, CuerpoTecnico(), Reglas()), "INS-08") == ["error"]


def test_ins_08_un_profe_que_cumple_todo_no_tiene_hallazgos() -> None:
    assert validar_alta_de_profe(profe(), CuerpoTecnico(), Reglas()) == []


# ---------- INS-09 y INS-10: dorsal y documento ----------


def test_ins_09_sin_dorsal_es_aviso_hasta_el_primer_partido() -> None:
    hallazgos = validar_alta_de_jugador(alta(dorsal=None), Reglas())
    assert niveles(hallazgos, "INS-09") == ["aviso"]


def test_ins_09_sin_dorsal_es_error_si_es_obligatorio_al_inscribir() -> None:
    hallazgos = validar_alta_de_jugador(
        alta(dorsal=None), reglas(dorsal_obligatorio="al_inscribir")
    )
    assert niveles(hallazgos, "INS-09") == ["error"]


def test_ins_09_dorsal_repetido_en_el_equipo_es_error() -> None:
    assert niveles(validar_alta_de_jugador(alta(dorsal=2), Reglas()), "INS-09") == ["error"]


@pytest.mark.parametrize("dorsal", [0, 100, -3])
def test_ins_09_dorsal_fuera_de_rango_es_error(dorsal: int) -> None:
    assert niveles(validar_alta_de_jugador(alta(dorsal=dorsal), Reglas()), "INS-09") == ["error"]


def test_ins_10_sin_documento_es_aviso_de_documento_pendiente() -> None:
    hallazgos = validar_alta_de_jugador(alta(documento=None), Reglas())
    assert niveles(hallazgos, "INS-10") == ["aviso"]
    assert "pendiente" in de_la_regla(hallazgos, "INS-10")[0].mensaje


def test_ins_10_sin_documento_es_error_si_es_obligatorio_al_inscribir() -> None:
    hallazgos = validar_alta_de_jugador(alta(documento=None), reglas(ci_obligatorio="al_inscribir"))
    assert niveles(hallazgos, "INS-10") == ["error"]


def test_ins_10_un_profe_sin_documento_tambien_queda_pendiente() -> None:
    hallazgos = validar_alta_de_profe(profe(documento=None), CuerpoTecnico(), Reglas())
    assert niveles(hallazgos, "INS-10") == ["aviso"]


# ---------- INS-11: cierre de inscripción ----------


def test_ins_11_sin_cierre_siempre_se_puede() -> None:
    assert validar_cierre(date(2026, 12, 1), Reglas(), es_organizacion=False) == []


def test_ins_11_despues_del_cierre_solo_la_organizacion() -> None:
    con_cierre = reglas(cierre_inscripcion=date(2026, 10, 20))
    assert validar_cierre(date(2026, 10, 20), con_cierre, es_organizacion=False) == []
    tarde = validar_cierre(date(2026, 10, 21), con_cierre, es_organizacion=False)
    assert [h.nivel for h in tarde] == ["error"]
    assert validar_cierre(date(2026, 10, 21), con_cierre, es_organizacion=True) == []
