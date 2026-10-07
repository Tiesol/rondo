"""Identidad del organizador (una instalación por cliente): nada propio de JMP va en el código."""

from typing import Any, ClassVar

from django.core.validators import RegexValidator
from django.db import models

_HEX = RegexValidator(r"^#[0-9a-fA-F]{6}$", "Tiene que ser un color hexadecimal, como #059669.")


class Organizador(models.Model):
    """Hay uno solo (pk=1). Se edita en el admin y aparece en las pantallas y en el PNG."""

    PK_UNICO: ClassVar[int] = 1

    nombre = models.CharField(max_length=80, default="JMP Soccer School")
    color_primario = models.CharField(max_length=7, default="#059669", validators=[_HEX])

    class Meta:
        verbose_name = "organizador"
        verbose_name_plural = "organizador"

    def __str__(self) -> str:
        return self.nombre

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.pk = self.PK_UNICO
        super().save(*args, **kwargs)

    @classmethod
    def actual(cls) -> Organizador:
        organizador, _ = cls.objects.get_or_create(pk=cls.PK_UNICO)
        return organizador
