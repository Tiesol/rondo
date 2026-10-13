"""Ajustes de una categoría-nivel (pestaña Ajustes de Torneo, TU.5)."""

from typing import TYPE_CHECKING, Any

from django import forms

from torneo.models import CategoriaNivel

if TYPE_CHECKING:
    _Base = forms.ModelForm[CategoriaNivel]
else:
    _Base = forms.ModelForm


DIAS = [
    ("lunes", "Lunes"),
    ("martes", "Martes"),
    ("miercoles", "Miércoles"),
    ("jueves", "Jueves"),
    ("viernes", "Viernes"),
    ("sabado", "Sábado"),
    ("domingo", "Domingo"),
]


class FormularioAjustes(_Base):
    dias_sin_jugar = forms.MultipleChoiceField(
        label="Días en que no juega",
        choices=DIAS,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Por ejemplo, Sub 5 y Sub 6 no juegan los viernes (P56).",
    )

    class Meta:
        model = CategoriaNivel
        fields = [
            "min_jugadores",
            "max_jugadores",
            "min_por_tiempo",
            "convocados_por_partido",
            "canchas",
            "dias_sin_jugar",
            "prefiere_temprano",
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


class FormularioNuevaCategoria(forms.Form):
    """T11.1: con el nombre y el nivel alcanza si la categoría es de la plantilla o ya tiene
    otro nivel; lo demás se completa solo y se corrige después en Ajustes."""

    nombre = forms.CharField(
        label="Categoría", max_length=50, widget=forms.TextInput(attrs={"list": "categorias"})
    )
    nivel = forms.ChoiceField(choices=CategoriaNivel.Nivel.choices, initial="avanzado")
    modalidad = forms.ChoiceField(
        choices=[("", "Como la plantilla"), *CategoriaNivel.Modalidad.choices], required=False
    )
    min_por_tiempo = forms.IntegerField(
        label="Minutos por tiempo", min_value=1, max_value=60, required=False
    )
    minimo = forms.IntegerField(label="Mínimo de jugadores", min_value=1, required=False)
    maximo = forms.IntegerField(label="Máximo de jugadores", min_value=1, required=False)
