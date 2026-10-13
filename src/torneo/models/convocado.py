"""La planilla del partido (T11.8, P9): quiénes juegan y con qué dorsal en ESTE partido. Muchos
equipos no tienen camisetas numeradas fijas: el dorsal del plantel es solo el habitual."""

from django.db import models

from torneo.models.fixture import Partido
from torneo.models.inscripcion import Equipo, Jugador


class Convocado(models.Model):
    partido = models.ForeignKey(Partido, on_delete=models.CASCADE, related_name="convocados")
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name="+")
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name="convocatorias")
    dorsal = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["partido", "equipo", "dorsal", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["partido", "jugador"], name="convocado_una_vez"),
            # P9: dos jugadores del mismo equipo con el mismo dorsal en un partido, imposible.
            models.UniqueConstraint(
                fields=["partido", "equipo", "dorsal"],
                condition=models.Q(dorsal__isnull=False),
                name="dorsal_unico_en_el_partido",
            ),
            models.CheckConstraint(
                condition=models.Q(dorsal__isnull=True) | models.Q(dorsal__gte=1, dorsal__lte=99),
                name="dorsal_del_partido_de_1_a_99",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.dorsal or 's/n'} · {self.partido}"
