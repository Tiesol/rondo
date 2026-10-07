"""TU.3: cada regla trae su título, su ayuda y su P#, y de ahí se arma la pantalla."""

from datetime import date

import pytest
from pydantic import Field

from dominio.config import Reglas, describir_reglas


def test_todas_las_reglas_tienen_titulo_ayuda_grupo_y_origen() -> None:
    descripciones = describir_reglas()
    assert [d.nombre for d in descripciones] == list(Reglas.model_fields)
    for d in descripciones:
        assert d.titulo and d.ayuda and d.grupo, d.nombre
        assert d.pregunta or d.regla, d.nombre


def test_los_tipos_se_deducen_del_modelo() -> None:
    por_nombre = {d.nombre: d for d in describir_reglas()}
    assert por_nombre["jugar_en_categoria_mayor"].tipo == "si_no"
    numero = por_nombre["propuestas_reprogramacion"]
    assert (numero.tipo, numero.minimo, numero.maximo) == ("numero", 1, 5)
    assert por_nombre["aviso_anios_menor"].minimo == 0
    assert por_nombre["cierre_inscripcion"].tipo == "fecha"
    assert por_nombre["marcador_wo"].tipo == "par"
    assert por_nombre["marcador_wo"].defecto == (3, 0)


def test_cada_opcion_tiene_su_etiqueta_en_espaniol() -> None:
    opcion = next(d for d in describir_reglas() if d.nombre == "jugador_en_dos_equipos")
    assert opcion.tipo == "opcion"
    assert dict(opcion.opciones) == {
        "mismo_club_otra_categoria": "Solo del mismo club, en otra categoría",
        "nunca": "Nunca",
    }


def test_una_regla_nueva_aparece_sin_tocar_nada_mas() -> None:
    class ReglasConUnaMas(Reglas):
        dias_de_gracia: int = Field(
            default=2,
            ge=0,
            title="Días de gracia",
            description="Inventada para el test.",
            json_schema_extra={"grupo": "Inscripción", "pregunta": "P99"},
        )

    nueva = describir_reglas(ReglasConUnaMas)[-1]
    assert (nueva.nombre, nueva.titulo, nueva.tipo, nueva.pregunta) == (
        "dias_de_gracia",
        "Días de gracia",
        "numero",
        "P99",
    )


def test_un_tipo_desconocido_falla_en_lugar_de_esconderse() -> None:
    class ReglasRaras(Reglas):
        rara: list[date] = Field(
            default=[], title="Rara", description="x", json_schema_extra={"grupo": "x"}
        )

    with pytest.raises(TypeError, match="rara"):
        describir_reglas(ReglasRaras)
