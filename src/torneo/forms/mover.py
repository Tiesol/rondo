"""Mover un partido a mano (T5.4)."""

from datetime import datetime
from typing import Any

from django import forms
from django.utils import timezone

from torneo.models import Cancha, Partido


class FormularioMover(forms.Form):
    dia = forms.DateField(label="Día", widget=forms.DateInput(attrs={"type": "date"}))
    hora = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time", "step": 300}))
    cancha = forms.ModelChoiceField(
        queryset=Cancha.objects.none(), empty_label=None, to_field_name="codigo"
    )

    def __init__(self, *args: Any, partido: Partido, **kwargs: Any) -> None:
        if partido.inicio is not None:
            local = timezone.localtime(partido.inicio)
            kwargs.setdefault(
                "initial", {"dia": local.date(), "hora": local.time(), "cancha": partido.cancha}
            )
        super().__init__(*args, **kwargs)
        campo = self.fields["cancha"]
        assert isinstance(campo, forms.ModelChoiceField)
        campo.queryset = Cancha.objects.filter(torneo=partido.categoria.torneo).order_by("codigo")

    def inicio(self) -> datetime:
        return timezone.make_aware(
            datetime.combine(self.cleaned_data["dia"], self.cleaned_data["hora"])
        )
