"""Ajustes de una categoría-nivel (pestaña Ajustes de Torneo, TU.5)."""

from typing import TYPE_CHECKING, Any

from django import forms

from torneo.models import CategoriaNivel

if TYPE_CHECKING:
    _Base = forms.ModelForm[CategoriaNivel]
else:
    _Base = forms.ModelForm


class FormularioAjustes(_Base):
    class Meta:
        model = CategoriaNivel
        fields = [
            "min_jugadores",
            "max_jugadores",
            "min_por_tiempo",
            "convocados_por_partido",
            "canchas",
        ]
        labels = {
            "min_jugadores": "Mínimo de jugadores",
            "max_jugadores": "Máximo de jugadores",
            "min_por_tiempo": "Minutos por tiempo",
            "convocados_por_partido": "Convocados por partido",
            "canchas": "Canchas donde puede jugar",
        }
        help_texts = {
            "convocados_por_partido": "Solo en fútbol 11. Vacío: todos los de la lista.",
        }
        widgets = {"canchas": forms.CheckboxSelectMultiple}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        campo = self.fields["canchas"]
        assert isinstance(campo, forms.ModelMultipleChoiceField)
        campo.queryset = self.instance.torneo.canchas.all()
        for nombre in ("min_jugadores", "max_jugadores", "min_por_tiempo"):
            self.fields[nombre].min_value = 1  # type: ignore[attr-defined]
            self.fields[nombre].widget.attrs["min"] = 1

    def clean(self) -> dict[str, Any]:
        datos = super().clean() or {}
        minimo, maximo = datos.get("min_jugadores"), datos.get("max_jugadores")
        if minimo is not None and maximo is not None and maximo < minimo:
            self.add_error("max_jugadores", "No puede ser menor que el mínimo.")
        convocados = datos.get("convocados_por_partido")
        if convocados is not None and maximo is not None and convocados > maximo:
            self.add_error("convocados_por_partido", "No puede superar el máximo de jugadores.")
        return datos
