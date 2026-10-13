"""Multas y suspensiones a mano (T8.9, P29 y P74)."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from torneo.models.fixture import Partido
from torneo.models.inscripcion import Jugador


class MultaPagada(models.Model):
    """La multa por doble amarilla de un jugador en un partido, ya pagada (P74)."""

    partido = models.ForeignKey(Partido, on_delete=models.CASCADE, related_name="multas")
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name="multas")
    registrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    registrada_en = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["partido", "jugador"], name="una_multa_por_partido")
        ]

    def __str__(self) -> str:
        return f"Multa pagada · {self.jugador} · {self.partido}"


class SuspensionManual(models.Model):
    """La que marca la organización (P29): después de `partido`, no juega los siguientes."""

    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name="suspensiones")
    partido = models.ForeignKey(Partido, on_delete=models.CASCADE, related_name="suspensiones")
    partidos = models.PositiveSmallIntegerField(default=1)
    motivo = models.CharField(max_length=120)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    creada_en = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.jugador} · {self.motivo}"
