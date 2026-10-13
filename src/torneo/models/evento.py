"""Lo que pasa en un partido (T8.5): goles, goles en contra y tarjetas, con quién y cuándo."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from torneo.models.fixture import Partido
from torneo.models.inscripcion import Equipo, Jugador


class Evento(models.Model):
    class Tipo(models.TextChoices):
        GOL = "gol", "Gol"
        GOL_EN_CONTRA = "gol_en_contra", "Gol en contra"
        AMARILLA = "amarilla", "Amarilla"
        ROJA = "roja", "Roja"

    partido = models.ForeignKey(Partido, on_delete=models.CASCADE, related_name="eventos")
    tipo = models.CharField(max_length=13, choices=Tipo.choices)
    # El equipo del jugador. En un gol en contra (P72), el que lo hizo: suma para el otro.
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name="+")
    jugador = models.ForeignKey(
        Jugador, on_delete=models.SET_NULL, null=True, blank=True, related_name="eventos"
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    creado_en = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["creado_en", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(tipo="gol_en_contra") | models.Q(jugador__isnull=True),
                name="gol_en_contra_sin_jugador",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} · {self.partido}"
