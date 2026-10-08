"""Bloqueos: los horarios en que un equipo no puede jugar (PRO-07, P21, P38)."""

from django.db import models

from torneo.models.configuracion import Torneo
from torneo.models.inscripcion import Equipo


class Bloqueo(models.Model):
    """Un partido de la ACF (u otro motivo aceptado) de uno o varios equipos. El organizador
    carga inicio y fin con el margen que quiera, incluido el traslado (P38)."""

    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name="bloqueos")
    equipos = models.ManyToManyField(Equipo, related_name="bloqueos")
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    motivo = models.CharField(max_length=80, default="Partido de la ACF")

    class Meta:
        ordering = ["inicio"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fin__gt=models.F("inicio")), name="bloqueo_fin_despues_de_inicio"
            )
        ]

    def __str__(self) -> str:
        return f"{self.motivo} ({self.inicio:%d/%m %H:%M})"
