from typing import TYPE_CHECKING

from django import forms

from torneo.models import Organizador

if TYPE_CHECKING:
    _Base = forms.ModelForm[Organizador]
else:
    _Base = forms.ModelForm


class FormularioEscuela(_Base):
    """Nombre y colores del organizador. Los colores se eligen con el selector del sistema."""

    class Meta:
        model = Organizador
        fields = ["nombre", "color_primario", "color_acento"]
        widgets = {
            "color_primario": forms.TextInput(attrs={"type": "color", "data-token": "--marca"}),
            "color_acento": forms.TextInput(attrs={"type": "color", "data-token": "--acento"}),
        }
