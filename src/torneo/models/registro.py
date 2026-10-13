"""Historial del partido (T11.7): con un solo rol (P64), es la única forma de saber quién se
equivocó. Guarda referencias, no nombres: al anonimizar a una persona, el historial la pierde."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from torneo.models.fixture import Partido
from torneo.models.inscripcion import Equipo, Jugador


class Registro(models.Model):
    partido = models.ForeignKey(Partido, on_delete=models.CASCADE, related_name="registros")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    fecha = models.DateTimeField(default=timezone.now)
    que = models.CharField(max_length=80)  # "Gol", "Dorsal", "W.O."
    equipo = models.ForeignKey(
        Equipo, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    jugador = models.ForeignKey(
        Jugador, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    antes = models.CharField(max_length=80, blank=True)
    despues = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["-fecha", "-pk"]

    def __str__(self) -> str:
        return f"{self.que} · {self.partido}"
