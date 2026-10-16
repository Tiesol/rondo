"""T13.33: un interruptor dentro de un formulario se ve como los de Reglas, no como una barra
amarilla. `.campo input` (ancho 100 %, alto 44 px, borde) le ganaba a `.interruptor`."""

import re
from pathlib import Path

import pytest
from django import forms
from django.template.loader import render_to_string

from torneo.forms.mover import FormularioMover
from torneo.views.calendario import FormularioDia

CSS = (Path(__file__).resolve().parents[2] / "frontend" / "tailwind.css").read_text()


def _solo(formulario: type[forms.Form], nombre: str) -> forms.BoundField:
    """El campo suelto, sin lo que el formulario necesita para armarse (partido, torneo)."""
    solo: forms.Form = type("Solo", (forms.Form,), {nombre: formulario.base_fields[nombre]})()
    return solo[nombre]


@pytest.mark.parametrize(
    ("formulario", "nombre"),
    [(FormularioDia, "fines_de_semana"), (FormularioMover, "fijar")],
    ids=["agregar tiempo", "mover"],
)
def test_el_interruptor_va_en_su_fila(formulario: type[forms.Form], nombre: str) -> None:
    html = render_to_string("parciales/campo.html", {"campo": _solo(formulario, nombre)})
    assert 'class="campo-interruptor"' in html
    assert 'class="campo"' not in html
    etiqueta, control = html.index("<label"), html.index('class="interruptor"')
    assert etiqueta < control  # el texto a la izquierda, el interruptor a la derecha


def test_un_campo_comun_sigue_igual() -> None:
    html = render_to_string("parciales/campo.html", {"campo": FormularioDia()["desde"]})
    assert 'class="campo"' in html and "campo-interruptor" not in html


def test_una_casilla_que_no_es_interruptor_sigue_como_campo() -> None:
    class Formulario(forms.Form):
        acepto = forms.BooleanField(required=False)

    html = render_to_string("parciales/campo.html", {"campo": Formulario()["acepto"]})
    assert "campo-interruptor" not in html


def test_el_css_de_los_campos_no_toca_los_interruptores() -> None:
    regla = re.search(r"\n  ([^\n{}]*\.campo input[^{]*)\{", CSS)
    assert regla is not None
    assert ".campo input:not(.interruptor)" in regla.group(1)
    assert re.search(r"\.campo-interruptor \{[^}]*display: flex", CSS)
