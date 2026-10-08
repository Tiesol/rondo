"""Agregar una persona y cambiar su rol (T6.2)."""

from typing import Any

from django import forms
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

ROLES = [("organizacion", "Organización"), ("mesa", "Mesa de control")]


class FormularioPersona(forms.Form):
    usuario = forms.CharField(
        max_length=30,
        validators=[RegexValidator(r"^[a-zA-Z0-9._-]+$", "Solo letras, números, punto y guion.")],
        help_text="Con lo que entra; sin espacios. Por ejemplo: mesa1 o ana.",
        widget=forms.TextInput(attrs={"autocapitalize": "none", "autocomplete": "off"}),
    )
    nombre = forms.CharField(max_length=60, required=False)
    rol = forms.ChoiceField(choices=ROLES)

    def clean_usuario(self) -> str:
        usuario: str = self.cleaned_data["usuario"].strip().lower()
        if User.objects.filter(username__iexact=usuario).exists():
            raise forms.ValidationError("Ya existe alguien con ese usuario.")
        return usuario


class FormularioRol(forms.Form):
    rol = forms.ChoiceField(choices=ROLES)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
