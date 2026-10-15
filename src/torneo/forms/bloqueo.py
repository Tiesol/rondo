"""Un equipo no puede jugar (T5.1, T13.15): equipos, día, horario y motivo del bloqueo.

La convocatoria 2026 no atiende pedidos particulares: los motivos son la ACF o una decisión de
la organización. La suspensión de un día (lluvia) va por "Suspender este día".
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from django import forms
from django.db.models import QuerySet
from django.utils import timezone

from torneo.models import Club, Equipo, Torneo

if TYPE_CHECKING:
    _CampoDeEquipos = forms.ModelMultipleChoiceField[Equipo]
else:
    _CampoDeEquipos = forms.ModelMultipleChoiceField


class _Equipos(_CampoDeEquipos):
    def label_from_instance(self, obj: Any) -> str:
        return f"{obj.nombre} · {obj.categoria}"


def clubes_del_torneo(torneo: Torneo) -> QuerySet[Club]:
    return Club.objects.filter(equipos__categoria__torneo=torneo).distinct().order_by("nombre")


MOTIVOS = [
    ("Partido de la ACF", "Partido de la ACF"),
    ("Decisión de la organización", "Decisión de la organización"),
]


class FormularioBloqueo(forms.Form):
    equipos = _Equipos(
        queryset=Equipo.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        help_text="Uno o varios: un partido de la ACF puede afectar a varios equipos del club.",
    )
    dia = forms.DateField(
        label="Día", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
    )
    desde = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    hasta = forms.TimeField(
        widget=forms.TimeInput(attrs={"type": "time"}), help_text="Con el margen del traslado."
    )
    motivo = forms.ChoiceField(choices=MOTIVOS, initial="Partido de la ACF")

    def __init__(self, *args: Any, torneo: Torneo, club: Any = None, **kwargs: Any) -> None:
        """T13.20: con `club`, se muestran solo sus equipos (se elige primero el club). Al
        guardar se acepta cualquier equipo del torneo."""
        super().__init__(*args, **kwargs)
        campo = self.fields["equipos"]
        assert isinstance(campo, forms.ModelMultipleChoiceField)
        campo.queryset = (
            Equipo.objects.filter(categoria__torneo=torneo)
            .select_related("categoria")
            .order_by("nombre", "categoria__edad", "categoria__nivel")
        )
        self.club = club
        if club is not None:
            campo.widget.choices = [
                (e.pk, campo.label_from_instance(e)) for e in campo.queryset.filter(club=club)
            ]

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


class FormularioReprogramar(forms.Form):
    """T13.15: reprogramar un partido. Quién no puede en ese horario, y por qué."""

    motivo = forms.ChoiceField(choices=MOTIVOS, initial="Partido de la ACF")
    equipos = forms.ModelMultipleChoiceField(
        queryset=Equipo.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="¿Quién no puede?",
        error_messages={"required": "Elige el equipo que no puede jugar."},
    )

    def __init__(self, *args: Any, partido: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        campo = self.fields["equipos"]
        assert isinstance(campo, forms.ModelMultipleChoiceField)
        campo.queryset = Equipo.objects.filter(pk__in=[partido.local_id, partido.visitante_id])
