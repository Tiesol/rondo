"""Formulario de las reglas del torneo, armado desde dominio.config.describir_reglas().

Agregar una regla al dominio la agrega acá y en la pantalla, sin tocar la plantilla.
"""

from typing import Any

from django import forms
from pydantic import ValidationError

from dominio.config import DescripcionRegla, Reglas, describir_reglas


class ParDeNumeros(forms.MultiValueField):
    """Dos números, como el marcador del W.O. (3 a 0)."""

    def __init__(self, **kwargs: Any) -> None:
        campos = (forms.IntegerField(min_value=0), forms.IntegerField(min_value=0))
        widget = forms.MultiWidget(
            widgets=[forms.NumberInput(attrs={"inputmode": "numeric", "min": 0})] * 2
        )
        super().__init__(fields=campos, widget=widget, **kwargs)

    def compress(self, data_list: list[int]) -> tuple[int, int] | None:
        return (data_list[0], data_list[1]) if data_list else None


def _campo(descripcion: DescripcionRegla) -> forms.Field:
    comunes: dict[str, Any] = {"label": descripcion.titulo, "help_text": descripcion.ayuda}
    match descripcion.tipo:
        case "si_no":
            return forms.BooleanField(
                required=False,
                widget=forms.CheckboxInput(attrs={"role": "switch", "class": "interruptor"}),
                **comunes,
            )
        case "numero":
            return forms.IntegerField(
                min_value=descripcion.minimo,
                max_value=descripcion.maximo,
                widget=forms.NumberInput(attrs={"inputmode": "numeric"}),
                **comunes,
            )
        case "opcion":
            return forms.ChoiceField(choices=descripcion.opciones, **comunes)
        case "fecha":
            return forms.DateField(
                required=False, widget=forms.DateInput(attrs={"type": "date"}), **comunes
            )
        case "par":
            return ParDeNumeros(**comunes)


class FormularioReglas(forms.Form):
    def __init__(self, *args: Any, modelo: type[Reglas] = Reglas, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.modelo = modelo
        self.descripciones = describir_reglas(modelo)
        for descripcion in self.descripciones:
            self.fields[descripcion.nombre] = _campo(descripcion)
            if descripcion.nombre not in self.initial:
                self.initial[descripcion.nombre] = descripcion.defecto

    def clean(self) -> dict[str, Any]:
        datos = super().clean() or {}
        if self.errors:
            return datos
        try:
            self.reglas = self.modelo.model_validate(datos)
        except ValidationError as error:
            for detalle in error.errors():
                campo = str(detalle["loc"][0]) if detalle["loc"] else None
                self.add_error(campo if campo in self.fields else None, detalle["msg"])
        return datos

    def grupos(self) -> list[tuple[str, list[tuple[DescripcionRegla, forms.BoundField]]]]:
        """Los campos por grupo (Inscripción, Fixture…), en el orden del dominio."""
        por_grupo: dict[str, list[tuple[DescripcionRegla, forms.BoundField]]] = {}
        for descripcion in self.descripciones:
            por_grupo.setdefault(descripcion.grupo, []).append(
                (descripcion, self[descripcion.nombre])
            )
        return list(por_grupo.items())
