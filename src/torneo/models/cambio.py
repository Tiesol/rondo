"""Historial de reprogramaciones y cambios a mano (ARQUITECTURA 6)."""

from django.conf import settings
from django.db import models

from torneo.models.configuracion import Cancha
from torneo.models.corrida import Corrida
from torneo.models.fixture import Partido


class Cambio(models.Model):
    partido = models.ForeignKey(Partido, on_delete=models.CASCADE, related_name="cambios")
    cancha_antes = models.ForeignKey(
        Cancha, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    inicio_antes = models.DateTimeField(null=True, blank=True)
    cancha_despues = models.ForeignKey(
        Cancha, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    inicio_despues = models.DateTimeField(null=True, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    fecha = models.DateTimeField(auto_now_add=True)
    motivo = models.CharField(max_length=120, blank=True)
    corrida = models.ForeignKey(
        Corrida, on_delete=models.SET_NULL, null=True, blank=True, related_name="cambios"
    )

    class Meta:
        ordering = ["-fecha", "-pk"]

    def __str__(self) -> str:
        return f"Cambio de {self.partido} ({self.fecha:%d/%m %H:%M})"
