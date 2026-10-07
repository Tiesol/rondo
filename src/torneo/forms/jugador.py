"""Alta de jugadores y profes (T2.6). Las reglas las aplica el dominio vía el servicio."""

from datetime import date
from typing import Any

from django import forms

from torneo.servicios.inscripcion import DatosPersona

_DOCUMENTO = forms.CharField(
    label="CI o pasaporte",
    required=False,
    max_length=30,
    help_text="Como venga: 1234567 SC, 1234567-1E, E-1234567. Vacío si todavía no lo tienes.",
    widget=forms.TextInput(attrs={"autocomplete": "off", "autocapitalize": "characters"}),
)


class _FormularioPersona(forms.Form):
    documento = _DOCUMENTO
    nombres = forms.CharField(max_length=80, widget=forms.TextInput(attrs={"autocomplete": "off"}))
    apellidos = forms.CharField(
        max_length=80, widget=forms.TextInput(attrs={"autocomplete": "off"})
    )


class FormularioJugador(_FormularioPersona):
    nacimiento = forms.DateField(label="Nacimiento", widget=forms.DateInput(attrs={"type": "date"}))
    dorsal = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={"inputmode": "numeric", "placeholder": "Opcional"}),
    )

    def datos(self) -> DatosPersona:
        return DatosPersona(
            self.cleaned_data["documento"],
            self.cleaned_data["nombres"],
            self.cleaned_data["apellidos"],
            self.cleaned_data["nacimiento"],
        )


class FormularioProfe(_FormularioPersona):
    rol = forms.ChoiceField()

    def __init__(self, *args: Any, roles: tuple[str, ...], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        campo = self.fields["rol"]
        assert isinstance(campo, forms.ChoiceField)
        campo.choices = [(rol, rol.capitalize()) for rol in roles]

    def datos(self) -> DatosPersona:
        return DatosPersona(
            self.cleaned_data["documento"],
            self.cleaned_data["nombres"],
            self.cleaned_data["apellidos"],
            None,
        )


def datos_a_medias(post: Any) -> tuple[DatosPersona, int | None]:
    """Lo que se escribió hasta ahora, para los avisos en vivo: lo que falta queda vacío."""
    try:
        nacimiento: date | None = date.fromisoformat(post.get("nacimiento", ""))
    except ValueError:
        nacimiento = None
    try:
        dorsal: int | None = int(post.get("dorsal", ""))
    except ValueError:
        dorsal = None
    datos = DatosPersona(
        post.get("documento", ""), post.get("nombres", ""), post.get("apellidos", ""), nacimiento
    )
    return datos, dorsal
