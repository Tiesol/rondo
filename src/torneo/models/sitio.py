"""Identidad del organizador (una instalación por cliente): nada propio de JMP va en el código."""

import re
from typing import Any, ClassVar

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from torneo.colores import AZUL_MARINO, BLANCO, contraste, texto_sobre

_PATRON_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_HEX = RegexValidator(_PATRON_HEX, "Tiene que ser un color hexadecimal, como #0d2440.")


def _se_lee_texto_blanco(color: str) -> None:
    """El color principal es el fondo de la barra y de la banda, con texto blanco encima."""
    if _PATRON_HEX.match(color) and contraste(color, BLANCO) < 4.5:
        raise ValidationError(
            "Elige un color más oscuro: el texto blanco tiene que leerse encima.",
            code="contraste",
        )


class Organizador(models.Model):
    """Hay uno solo (pk=1). Se edita en el admin y aparece en las pantallas y en el PNG."""

    PK_UNICO: ClassVar[int] = 1

    nombre = models.CharField(max_length=80, default="JMP Soccer School")
    color_primario = models.CharField(
        "color principal",
        max_length=7,
        default=AZUL_MARINO,
        validators=[_HEX, _se_lee_texto_blanco],
        help_text="La barra superior, la banda y los botones principales. Con texto blanco encima.",
    )
    color_acento = models.CharField(
        "color de acento",
        max_length=7,
        default="#f2cf3a",
        validators=[_HEX],
        help_text="Lo que resalta: la pestaña activa, la selección y el año del torneo.",
    )

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

    @property
    def sigla(self) -> str:
        """La marca redonda de la barra: "JMP Soccer School" da "JMP"; "Club Bolívar", "CB"."""
        palabras = self.nombre.split()
        if not palabras:
            return ""
        if palabras[0].isupper() and len(palabras[0]) > 1:
            return palabras[0][:4]
        return "".join(p[0] for p in palabras[:3]).upper()

    @property
    def texto_sobre_acento(self) -> str:
        return texto_sobre(self.color_acento)
