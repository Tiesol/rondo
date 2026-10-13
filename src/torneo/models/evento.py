"""Lo que pasa en un partido (T8.5 y T11.10): goles, goles en contra, tarjetas, amonestaciones
y lesiones, con el minuto, quién lo cargó y cuándo. Amonestación y lesión son internas: nunca
se publican (la lesión es un dato de salud de un menor)."""

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
        AMONESTACION = "amonestacion", "Amonestación"  # verbal, Sub 5 a Sub 7 (T10.9)
        LESION = "lesion", "Lesión"  # T11.10: interna, nunca pública

    partido = models.ForeignKey(Partido, on_delete=models.CASCADE, related_name="eventos")
    tipo = models.CharField(max_length=13, choices=Tipo.choices)
    # El equipo del jugador. En un gol en contra (P72), el del que lo hizo: suma para el otro.
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name="+")
    jugador = models.ForeignKey(
        Jugador, on_delete=models.SET_NULL, null=True, blank=True, related_name="eventos"
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    creado_en = models.DateTimeField(default=timezone.now)
    minuto = models.PositiveSmallIntegerField(null=True, blank=True)  # T11.10: del reloj

    class Meta:
        ordering = ["creado_en", "pk"]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} · {self.partido}"
