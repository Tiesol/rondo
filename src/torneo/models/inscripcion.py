"""Inscripción: clubes, equipos y personas (ARQUITECTURA, sección 6).

Persona es la única tabla con datos personales (son menores): nada fuera de ella guarda
nombres, CI ni fechas de nacimiento. Las listas reales nunca entran al repo.
"""

from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower

from torneo.models.configuracion import CategoriaNivel

_HEX = RegexValidator(r"^#[0-9a-fA-F]{6}$", "Tiene que ser un color hexadecimal, como #c8102e.")


def _validar_alias(valor: Any) -> None:
    if not isinstance(valor, list) or not all(isinstance(a, str) and a.strip() for a in valor):
        raise ValidationError("Los alias son una lista de nombres.")


class Club(models.Model):
    """Catálogo: el club se elige, no se escribe. Los alias son otras formas de nombrarlo."""

    nombre = models.CharField(max_length=80)
    alias = models.JSONField(default=list, blank=True, validators=[_validar_alias])

    class Meta:
        ordering = ["nombre"]
        constraints = [models.UniqueConstraint(Lower("nombre"), name="club_nombre_unico")]

    def __str__(self) -> str:
        return self.nombre

    @classmethod
    def buscar(cls, texto: str) -> Club | None:
        """El club por su nombre o un alias, sin distinguir mayúsculas."""
        buscado = texto.strip().casefold()
        for club in cls.objects.all():
            if buscado in {club.nombre.casefold(), *(a.casefold() for a in club.alias)}:
                return club
        return None


class Equipo(models.Model):
    """Un club en una categoría-nivel (INS-01). Puede haber dos del mismo club."""

    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name="equipos")
    categoria = models.ForeignKey(CategoriaNivel, on_delete=models.PROTECT, related_name="equipos")
    nombre = models.CharField("nombre visible", max_length=80)
    color_1 = models.CharField("color 1", max_length=7, blank=True, validators=[_HEX])
    color_2 = models.CharField("color 2", max_length=7, blank=True, validators=[_HEX])
    pagado = models.BooleanField(default=False)

    class Meta:
        ordering = ["categoria", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["club", "categoria", "nombre"], name="equipo_unico_por_club_y_categoria"
            )
        ]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.categoria})"


class Persona(models.Model):
    """La única tabla con datos personales. Sirve para jugadores y profes."""

    class TipoDocumento(models.TextChoices):
        PENDIENTE = "", "Pendiente"
        CI = "ci", "CI"
        CI_EXTRANJERO = "ci_extranjero", "CI de extranjero"
        PASAPORTE = "pasaporte", "Pasaporte"

    tipo_documento = models.CharField(
        max_length=13, choices=TipoDocumento.choices, blank=True, default=""
    )
    documento = models.CharField(max_length=30, blank=True, help_text="Como se muestra")
    clave_documento = models.CharField(
        max_length=30, blank=True, help_text="Para comparar (dominio.documentos)"
    )
    nombres = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=80)
    nacimiento = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["apellidos", "nombres"]
        constraints = [
            models.UniqueConstraint(
                fields=["clave_documento"],
                condition=~models.Q(clave_documento=""),
                name="documento_unico_si_existe",
            )
        ]

    def __str__(self) -> str:
        return f"{self.nombres} {self.apellidos}"


class Jugador(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="jugadores")
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name="jugadores")
    dorsal = models.PositiveSmallIntegerField(null=True, blank=True)
    verificado = models.BooleanField(default=False, help_text="La mesa vio el documento (INS-12)")

    class Meta:
        verbose_name_plural = "jugadores"
        ordering = ["equipo", "dorsal"]
        constraints = [
            models.UniqueConstraint(fields=["equipo", "persona"], name="jugador_una_vez"),
            models.UniqueConstraint(
                fields=["equipo", "dorsal"],
                condition=models.Q(dorsal__isnull=False),
                name="dorsal_unico_en_el_equipo",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.persona} ({self.equipo})"


class Profe(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="profes")
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name="profes")
    rol = models.CharField(max_length=20, help_text="Uno de los roles del cuerpo técnico")

    class Meta:
        ordering = ["equipo", "rol"]
        constraints = [models.UniqueConstraint(fields=["equipo", "persona"], name="profe_una_vez")]

    def __str__(self) -> str:
        return f"{self.persona} ({self.rol}, {self.equipo})"
