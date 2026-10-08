"""Cada ejecución del solver (ARQUITECTURA 6 y 8)."""

from django.conf import settings
from django.db import models

from torneo.models.configuracion import Torneo


class Corrida(models.Model):
    class Tipo(models.TextChoices):
        PROGRAMAR = "programar", "Programar"
        REPROGRAMAR = "reprogramar", "Reprogramar"

    class Estado(models.TextChoices):
        CORRIENDO = "corriendo", "Corriendo"
        TERMINADA = "terminada", "Terminada"
        FALLIDA = "fallida", "Falló"

    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name="corridas")
    tipo = models.CharField(max_length=11, choices=Tipo.choices, default=Tipo.PROGRAMAR)
    estado = models.CharField(max_length=9, choices=Estado.choices, default=Estado.CORRIENDO)
    parametros = models.JSONField(default=dict, blank=True)
    # Cuántos se ubicaron, los que no (con su motivo) y los choques del verificador.
    resultado = models.JSONField(default=dict, blank=True)
    inicio = models.DateTimeField(auto_now_add=True)
    duracion = models.FloatField("duración (s)", null=True, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-inicio"]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} {self.torneo} ({self.get_estado_display()})"
