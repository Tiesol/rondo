"""La planilla del partido (T11.8, P9): quiénes juegan y con qué dorsal en ESTE partido. Muchos
equipos no tienen camisetas numeradas fijas: el dorsal del plantel es solo el habitual.

C1 (fase 12): un dorsal repetido en el partido es un aviso, no un bloqueo: la base no lo impide."""

from django.db import models

from torneo.models.fixture import Partido
from torneo.models.inscripcion import Equipo, Jugador


class Convocado(models.Model):
    partido = models.ForeignKey(Partido, on_delete=models.CASCADE, related_name="convocados")
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name="+")
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name="convocatorias")
    dorsal = models.PositiveSmallIntegerField(null=True, blank=True)
    # C2 (fase 12): la mesa vio el CI de este jugador en este partido. No bloquea nada.
    ci_verificado = models.BooleanField(default=False)

    class Meta:
        ordering = ["partido", "equipo", "dorsal", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["partido", "jugador"], name="convocado_una_vez"),
            models.CheckConstraint(
                condition=models.Q(dorsal__isnull=True) | models.Q(dorsal__gte=1, dorsal__lte=99),
                name="dorsal_del_partido_de_1_a_99",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.dorsal or 's/n'} · {self.partido}"
