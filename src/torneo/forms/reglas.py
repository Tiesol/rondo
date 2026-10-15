"""Formulario de las reglas del torneo, armado desde dominio.config.describir_reglas().

Agregar una regla al dominio la agrega acá y en la pantalla, sin tocar la plantilla.
"""

from datetime import date
from typing import Any

from django import forms
from django.utils import timezone
from pydantic import ValidationError

from dominio.config import DescripcionRegla, Reglas, describir_reglas
from torneo.models import Franja, Torneo


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
        case "fecha_hora":
            return forms.DateTimeField(
                required=False,
                input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"],
                widget=forms.DateTimeInput(
                    attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
                ),
                **comunes,
            )
        case "par":
            return ParDeNumeros(**comunes)


def _categorias(torneo: Torneo, actual: Any) -> list[tuple[int, str]]:
    """T13.28: "Sub N" de las categorías del torneo (y el valor de hoy, aunque no esté)."""
    edades = set(torneo.categorias.values_list("edad", flat=True))
    if isinstance(actual, int):
        edades.add(actual)
    return [(edad, f"Sub {edad}") for edad in sorted(edades)]


def _fines_de_semana(torneo: Torneo, actual: Any) -> list[tuple[int, str]]:
    """T13.28: los fines de semana del torneo con sus fechas: "4.º: 14 y 15/11"."""
    semanas: dict[tuple[int, int], list[date]] = {}
    for franja in torneo.franjas.filter(tipo=Franja.Tipo.REGULAR):
        dia = timezone.localtime(franja.inicio).date()
        semanas.setdefault(dia.isocalendar()[:2], []).append(dia)
    opciones = []
    for numero, (_, dias) in enumerate(sorted(semanas.items()), start=1):
        finde = sorted({d for d in dias if d.weekday() >= 5}) or sorted(set(dias))
        nombres = [str(d.day) for d in finde]
        texto = " y ".join([", ".join(nombres[:-1]), nombres[-1]] if len(nombres) > 1 else nombres)
        opciones.append((numero, f"{numero}.º: {texto}/{finde[-1].month}"))
    if isinstance(actual, int) and actual > len(opciones):
        opciones.append((actual, f"{actual}.º (fuera del torneo)"))
    return opciones


LISTAS = {"doble_amarilla_desde": _categorias, "eliminacion_desde_fin_de_semana": _fines_de_semana}


class FormularioReglas(forms.Form):
    def __init__(
        self,
        *args: Any,
        modelo: type[Reglas] = Reglas,
        torneo: Torneo | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.modelo = modelo
        self.descripciones = describir_reglas(modelo)
        for descripcion in self.descripciones:
            self.fields[descripcion.nombre] = _campo(descripcion)
            if descripcion.nombre not in self.initial:
                self.initial[descripcion.nombre] = descripcion.defecto
            # T13.28: con el torneo creado, estas se eligen de una lista.
            if torneo is not None and descripcion.nombre in LISTAS:
                opciones = LISTAS[descripcion.nombre](torneo, self.initial[descripcion.nombre])
                self.fields[descripcion.nombre] = forms.TypedChoiceField(
                    choices=opciones,
                    coerce=int,
                    label=descripcion.titulo,
                    help_text=descripcion.ayuda,
                )

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
