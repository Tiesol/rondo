"""Formularios de reprogramar: dónde se juega lo suspendido (B1) y qué reglas se aflojan solo
esta vez (B6)."""

from datetime import date, time
from typing import Any

from django import forms

from dominio.programador.relajar import Relajar
from torneo.models import Cancha, Torneo


class CamposAflojar(forms.Form):
    """Reglas que se aflojan solo para esta corrida. Las del torneo no cambian."""

    turnos_libres = forms.IntegerField(
        required=False, min_value=0, max_value=5, label="Turnos libres entre partidos del día"
    )
    max_por_dia = forms.IntegerField(
        required=False, min_value=1, max_value=6, label="Máximo de partidos por equipo y día"
    )
    orden_blando = forms.BooleanField(required=False, label="Las fechas pueden quedar al revés")
    minutos_extra = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=180,
        label="Empezar antes o terminar después (minutos)",
    )
    usar_mitades = forms.BooleanField(required=False, label="Usar mitades de cancha")

    def relajar(self) -> Relajar:
        datos = self.cleaned_data
        return Relajar(
            turnos_libres=datos.get("turnos_libres"),
            max_por_dia=datos.get("max_por_dia"),
            orden="blanda" if datos.get("orden_blando") else None,
            minutos_extra=datos.get("minutos_extra") or 0,
            usar_mitades=bool(datos.get("usar_mitades")),
        )


class FormularioSuspension(CamposAflojar):
    """Dónde se juega lo suspendido: un día, un horario y las canchas donde vale."""

    dia = forms.DateField(
        label="Día", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
    )
    desde = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    hasta = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    canchas = forms.ModelMultipleChoiceField(
        queryset=Cancha.objects.none(),
        required=False,
        label="Canchas donde vale",
        help_text="Sin elegir: todas.",
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args: Any, torneo: Torneo, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["canchas"].queryset = Cancha.objects.filter(  # type: ignore[attr-defined]
            torneo=torneo, padre__isnull=True
        )

    def clean(self) -> dict[str, Any]:
        datos = super().clean() or {}
        if datos.get("desde") and datos.get("hasta") and datos["hasta"] <= datos["desde"]:
            self.add_error("hasta", "Tiene que ser después de «desde».")
        return datos

    @staticmethod
    def inicial(dia: date, desde: time, hasta: time) -> dict[str, Any]:
        return {"dia": dia, "desde": desde.strftime("%H:%M"), "hasta": hasta.strftime("%H:%M")}
