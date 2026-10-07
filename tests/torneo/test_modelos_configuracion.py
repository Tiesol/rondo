"""T1.3: modelos de configuración con sus restricciones en la base."""

from datetime import UTC, date, datetime

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from dominio.config import Reglas
from torneo.models import Cancha, CategoriaNivel, Franja, Torneo


def _torneo(**cambios: object) -> Torneo:
    datos: dict[str, object] = {
        "nombre": "JMP CUP 2026",
        "edicion": 5,
        "anio": 2026,
        "inicio": date(2026, 10, 23),
        "fin": date(2026, 11, 22),
    }
    return Torneo.objects.create(**(datos | cambios))


def _categoria_nivel(torneo: Torneo, **cambios: object) -> CategoriaNivel:
    datos: dict[str, object] = {
        "torneo": torneo,
        "categoria": "Sub 9",
        "edad": 9,
        "nivel": "inicial",
        "modalidad": "F7",
        "min_jugadores": 12,
        "max_jugadores": 14,
        "min_por_tiempo": 20,
    }
    return CategoriaNivel.objects.create(**(datos | cambios))


@pytest.mark.django_db
def test_un_torneo_nuevo_tiene_las_reglas_por_defecto() -> None:
    torneo = _torneo()
    assert Reglas.model_validate(torneo.reglas) == Reglas()


@pytest.mark.django_db
def test_reglas_invalidas_son_un_error_de_validacion_y_no_se_guardan() -> None:
    with pytest.raises(ValidationError, match="max_partidos_por_dia"):
        _torneo(reglas={"max_partidos_por_dia": "dos"})
    assert not Torneo.objects.exists()


@pytest.mark.django_db
def test_el_codigo_de_cancha_es_unico_por_torneo() -> None:
    torneo = _torneo()
    Cancha.objects.create(torneo=torneo, codigo="C1", nombre="Cancha 1")
    with pytest.raises(IntegrityError):
        Cancha.objects.create(torneo=torneo, codigo="C1", nombre="Otra")


@pytest.mark.django_db
def test_la_cancha_entera_conoce_sus_mitades() -> None:
    torneo = _torneo()
    c1 = Cancha.objects.create(torneo=torneo, codigo="C1", nombre="Cancha 1")
    Cancha.objects.create(torneo=torneo, codigo="C1A", nombre="Cancha 1 A", padre=c1)
    Cancha.objects.create(torneo=torneo, codigo="C1B", nombre="Cancha 1 B", padre=c1)
    assert sorted(c1.mitades.values_list("codigo", flat=True)) == ["C1A", "C1B"]


@pytest.mark.django_db
def test_categoria_y_nivel_son_unicos_por_torneo() -> None:
    torneo = _torneo()
    _categoria_nivel(torneo)
    with pytest.raises(IntegrityError):
        _categoria_nivel(torneo)


@pytest.mark.django_db
def test_el_maximo_de_jugadores_no_puede_ser_menor_que_el_minimo() -> None:
    with pytest.raises(IntegrityError):
        _categoria_nivel(_torneo(), min_jugadores=14, max_jugadores=12)


@pytest.mark.django_db
def test_la_categoria_nivel_calcula_partido_y_turno_con_la_configuracion_del_torneo() -> None:
    sub9 = _categoria_nivel(_torneo())
    assert (sub9.minutos_partido, sub9.minutos_turno) == (45, 50)


@pytest.mark.django_db
def test_una_franja_tiene_que_terminar_despues_de_empezar() -> None:
    momento = datetime(2026, 10, 23, 20, 0, tzinfo=UTC)
    with pytest.raises(IntegrityError):
        Franja.objects.create(torneo=_torneo(), inicio=momento, fin=momento)


@pytest.mark.django_db
def test_las_franjas_se_guardan_en_utc_y_se_muestran_en_hora_de_bolivia() -> None:
    franja = Franja.objects.create(
        torneo=_torneo(),
        inicio=datetime(2026, 10, 23, 20, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 24, 0, 0, tzinfo=UTC),
    )
    franja.refresh_from_db()
    assert timezone.localtime(franja.inicio).hour == 16
