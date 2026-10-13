"""Patrocinadores de un torneo (P69): imagen, nombre y orden. Cambian de un año a otro."""

from django.db import models

from torneo.models.configuracion import Torneo


class Patrocinador(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name="patrocinadores")
    nombre = models.CharField(max_length=80)
    imagen = models.FileField(max_length=200)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "pk"]
        verbose_name_plural = "patrocinadores"

    def __str__(self) -> str:
        return self.nombre
