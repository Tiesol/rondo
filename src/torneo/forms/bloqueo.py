"""Partido de la ACF (T5.1): equipos, día y horario del bloqueo."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from django import forms
from django.utils import timezone

from torneo.models import Equipo, Torneo

if TYPE_CHECKING:
    _CampoDeEquipos = forms.ModelMultipleChoiceField[Equipo]
else:
    _CampoDeEquipos = forms.ModelMultipleChoiceField


class _Equipos(_CampoDeEquipos):
    def label_from_instance(self, obj: Any) -> str:
        return f"{obj.nombre} · {obj.categoria}"


class FormularioBloqueo(forms.Form):
    equipos = _Equipos(
        queryset=Equipo.objects.none(),
        widget=forms.SelectMultiple(attrs={"size": 8}),
        help_text="Uno o varios: un partido de la ACF puede afectar a varios equipos del club.",
    )
    dia = forms.DateField(label="Día", widget=forms.DateInput(attrs={"type": "date"}))
    desde = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    hasta = forms.TimeField(
        widget=forms.TimeInput(attrs={"type": "time"}), help_text="Con el margen del traslado."
    )
    motivo = forms.CharField(max_length=80, initial="Partido de la ACF")

    def __init__(self, *args: Any, torneo: Torneo, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        campo = self.fields["equipos"]
        assert isinstance(campo, forms.ModelMultipleChoiceField)
        campo.queryset = (
            Equipo.objects.filter(categoria__torneo=torneo)
            .select_related("categoria")
            .order_by("nombre", "categoria")
        )

    def clean(self) -> dict[str, Any]:
        datos = super().clean() or {}
        desde, hasta = datos.get("desde"), datos.get("hasta")
        if desde and hasta and hasta <= desde:
            self.add_error("hasta", "Tiene que ser después de «desde».")
        return datos

    def momento(self, campo: str) -> datetime:
        return timezone.make_aware(
            datetime.combine(self.cleaned_data["dia"], self.cleaned_data[campo])
        )
