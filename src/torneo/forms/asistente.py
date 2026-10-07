"""Formularios de los pasos 1 a 3 del asistente. El paso 4 es el de las reglas (TU.3)."""

from datetime import date, time
from typing import Any

from django import forms

from torneo.models import Torneo
from torneo.servicios.asistente import DIAS, NOMBRE_DEL_DIA


class FormularioDatos(forms.Form):
    nombre = forms.CharField(max_length=100)
    edicion = forms.IntegerField(label="Edición", min_value=1)
    inicio = forms.DateField(label="Empieza", widget=forms.DateInput(attrs={"type": "date"}))
    fin = forms.DateField(label="Termina", widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self) -> dict[str, Any]:
        datos = super().clean() or {}
        inicio, fin, nombre = datos.get("inicio"), datos.get("fin"), datos.get("nombre")
        if inicio and fin and fin < inicio:
            self.add_error("fin", "Tiene que ser después del inicio.")
        if inicio and nombre and Torneo.objects.filter(nombre=nombre, anio=inicio.year).exists():
            self.add_error(
                "nombre",
                f"Ya existe un torneo «{nombre}» en {inicio.year}. "
                "Usa otro nombre o cambia ese torneo desde su pantalla.",
            )
        return datos

    def respuesta(self) -> dict[str, Any]:
        datos = self.cleaned_data
        inicio: date = datos["inicio"]
        fin: date = datos["fin"]
        return {
            "nombre": datos["nombre"],
            "edicion": datos["edicion"],
            "inicio": inicio.isoformat(),
            "fin": fin.isoformat(),
        }


class FormularioNiveles(forms.Form):
    niveles = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Elige al menos una categoría."},
    )

    def __init__(self, *args: Any, niveles: list[dict[str, str]], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.info = niveles
        campo = self.fields["niveles"]
        assert isinstance(campo, forms.MultipleChoiceField)
        campo.choices = [(n["clave"], n["titulo"]) for n in niveles]

    def filas(self) -> list[dict[str, Any]]:
        elegidos = set(self["niveles"].value() or [])
        return [n | {"elegido": n["clave"] in elegidos} for n in self.info]


class FormularioFranjas(forms.Form):
    """Un horario por día de la semana; los días apagados no tienen partidos."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for dia in DIAS:
            self.fields[f"{dia}_activo"] = forms.BooleanField(
                required=False,
                label=NOMBRE_DEL_DIA[dia],
                widget=forms.CheckboxInput(attrs={"role": "switch", "class": "interruptor"}),
            )
            for borde in ("inicio", "fin"):
                self.fields[f"{dia}_{borde}"] = forms.TimeField(
                    required=False,
                    label=f"{NOMBRE_DEL_DIA[dia]}: {'desde' if borde == 'inicio' else 'hasta'}",
                    widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
                )

    @staticmethod
    def iniciales(franjas: dict[str, list[str]]) -> dict[str, Any]:
        datos: dict[str, Any] = {}
        for dia in DIAS:
            datos[f"{dia}_activo"] = dia in franjas
            inicio, fin = franjas.get(dia, ["08:00", "16:00"])
            datos[f"{dia}_inicio"], datos[f"{dia}_fin"] = inicio, fin
        return datos

    def clean(self) -> dict[str, Any]:
        datos = super().clean() or {}
        activos = [dia for dia in DIAS if datos.get(f"{dia}_activo")]
        if not activos:
            raise forms.ValidationError("Elige al menos un día de juego.")
        for dia in activos:
            inicio: time | None = datos.get(f"{dia}_inicio")
            fin: time | None = datos.get(f"{dia}_fin")
            if inicio is None or fin is None:
                self.add_error(f"{dia}_inicio", "Falta el horario.")
            elif fin <= inicio:
                self.add_error(f"{dia}_fin", "Tiene que terminar después de empezar.")
        return datos

    def dias(self) -> list[dict[str, Any]]:
        return [
            {
                "nombre": NOMBRE_DEL_DIA[dia],
                "activo": self[f"{dia}_activo"],
                "inicio": self[f"{dia}_inicio"],
                "fin": self[f"{dia}_fin"],
            }
            for dia in DIAS
        ]

    def respuesta(self) -> dict[str, list[str]]:
        datos = self.cleaned_data
        return {
            dia: [datos[f"{dia}_inicio"].strftime("%H:%M"), datos[f"{dia}_fin"].strftime("%H:%M")]
            for dia in DIAS
            if datos.get(f"{dia}_activo")
        }
