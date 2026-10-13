"""Sorteo de la tabla (P28): si después del fair play siguen empatados, lo hace la organización
y lo registra acá. Lugar 1 es el mejor entre los empatados."""

from django.db import models

from torneo.models.configuracion import CategoriaNivel
from torneo.models.inscripcion import Equipo


class SorteoDeTabla(models.Model):
    categoria = models.ForeignKey(CategoriaNivel, on_delete=models.CASCADE, related_name="sorteos")
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name="+")
    lugar = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["categoria", "equipo"], name="un_sorteo_por_equipo")
        ]

    def __str__(self) -> str:
        return f"{self.equipo} · lugar {self.lugar} en el sorteo"
