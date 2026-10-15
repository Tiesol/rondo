"""T13.28: en Reglas, "Doble amarilla es roja desde" se elige de las categorías del torneo y el
fin de semana de la eliminación, de las fechas reales. En el asistente (sin torneo todavía)
siguen siendo números."""

import pytest
from django.conf import settings

from dominio.config import cargar_config
from torneo.forms.reglas import FormularioReglas
from torneo.models import Torneo
from torneo.servicios.configuracion import cargar_configuracion


@pytest.fixture
def torneo() -> Torneo:
    return cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))


@pytest.mark.django_db
def test_doble_amarilla_se_elige_de_las_categorias(torneo: Torneo) -> None:
    form = FormularioReglas(initial=dict(torneo.reglas), torneo=torneo)
    opciones = dict(form.fields["doble_amarilla_desde"].choices)  # type: ignore[attr-defined]
    assert opciones[10] == "Sub 10" and opciones[5] == "Sub 5"
    assert 1 not in opciones


@pytest.mark.django_db
def test_el_fin_de_semana_de_la_eliminacion_con_sus_fechas(torneo: Torneo) -> None:
    form = FormularioReglas(initial=dict(torneo.reglas), torneo=torneo)
    opciones = dict(form.fields["eliminacion_desde_fin_de_semana"].choices)  # type: ignore[attr-defined]
    assert opciones[1] == "1.º: 24 y 25/10"
    assert opciones[4] == "4.º: 14 y 15/11"


@pytest.mark.django_db
def test_guardar_con_las_listas(torneo: Torneo) -> None:
    form = FormularioReglas(initial=dict(torneo.reglas), torneo=torneo)
    datos = {}
    for nombre in form.fields:
        valor = form.initial.get(nombre)
        if isinstance(valor, bool):
            if valor:
                datos[nombre] = "on"
        elif isinstance(valor, (list, tuple)):
            datos[f"{nombre}_0"], datos[f"{nombre}_1"] = (str(v) for v in valor)
        elif valor is not None:
            datos[nombre] = str(valor)
    datos |= {"doble_amarilla_desde": "11", "eliminacion_desde_fin_de_semana": "3"}
    form = FormularioReglas(datos, torneo=torneo)
    assert form.is_valid(), form.errors
    assert form.reglas.doble_amarilla_desde == 11
    assert form.reglas.eliminacion_desde_fin_de_semana == 3


def test_sin_torneo_siguen_siendo_numeros() -> None:
    form = FormularioReglas()
    assert not hasattr(form.fields["doble_amarilla_desde"], "choices")
