"""Inscripción: clubes, equipos y personas (ARQUITECTURA, sección 6).

Persona es la única tabla con datos personales (son menores): nada fuera de ella guarda
nombres, CI ni fechas de nacimiento. Las listas reales nunca entran al repo.
"""

from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower

from dominio.nacimiento import Nacimiento
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


class EquipoDeClub(models.Model):
    """Un equipo de un club, con su escudo (T13.1; P68, P88 y P89). El nombre lo identifica
    dentro del club, y juega en una o varias categorías: cada una es un `Equipo`. Un club puede
    tener cualquier cantidad."""

    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name="equipos_del_club")
    nombre = models.CharField(max_length=80)
    # Uno por equipo; vale en todas sus categorías. Lo sube la organización (T8.3).
    escudo = models.FileField(max_length=200, blank=True)

    class Meta:
        verbose_name = "equipo del club"
        verbose_name_plural = "equipos del club"
        ordering = ["club", "nombre"]
        constraints = [
            models.UniqueConstraint("club", Lower("nombre"), name="equipo_de_club_unico")
        ]

    def __str__(self) -> str:
        return self.nombre

    @classmethod
    def del_club(cls, club: Club, nombre: str) -> EquipoDeClub:
        """El equipo del club con ese nombre (sin distinguir mayúsculas); si no hay, lo crea."""
        nombre = nombre.strip()
        return cls.objects.filter(club=club, nombre__iexact=nombre).first() or cls.objects.create(
            club=club, nombre=nombre
        )


class Equipo(models.Model):
    """Un equipo del club en una categoría-nivel (INS-01). Puede haber dos del mismo club, con
    nombres distintos (P89)."""

    equipo_de_club = models.ForeignKey(
        EquipoDeClub, on_delete=models.PROTECT, related_name="equipos"
    )
    # Copias de equipo_de_club, para las consultas y el orden. Cambian solo con
    # servicios.equipos.renombrar_equipo y unir_clubes, que actualizan las dos cosas juntas.
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
                fields=["equipo_de_club", "categoria"],
                name="equipo_unico_por_categoria",
                violation_error_message=(
                    "Ya hay un equipo con ese nombre, de ese club, en esa categoría."
                ),
            )
        ]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.categoria})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.equipo_de_club_id is None:
            self.equipo_de_club = EquipoDeClub.del_club(self.club, self.nombre)
        del_club = self.equipo_de_club
        if self.pk is None or not self.nombre:
            self.nombre, self.club_id = del_club.nombre, del_club.club_id
        elif (self.nombre, self.club_id) != (del_club.nombre, del_club.club_id):
            raise ValueError(
                "El nombre y el club de un equipo se cambian con renombrar_equipo o unir_clubes."
            )
        super().save(*args, **kwargs)


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
    # El año alcanza para la regla de edad (INS-02); la fecha completa, si se conoce (T7.6).
    anio_nacimiento = models.PositiveSmallIntegerField("año de nacimiento", null=True, blank=True)
    nacimiento = models.DateField("fecha de nacimiento", null=True, blank=True)
    # Foto (T8.4, P67 y P75): la manda el jugador con el uniforme y la sube la organización.
    # Sin la autorización de la familia (P66), no sale en ningún lado público.
    foto = models.FileField(max_length=200, blank=True)
    foto_autorizada = models.BooleanField("autoriza foto y nombre", default=False)
    foto_autorizada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    foto_autorizada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["apellidos", "nombres"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(nacimiento__isnull=True)
                | models.Q(
                    anio_nacimiento__isnull=False, nacimiento__year=models.F("anio_nacimiento")
                ),
                name="fecha_de_nacimiento_del_mismo_anio",
            ),
            models.UniqueConstraint(
                fields=["clave_documento"],
                condition=~models.Q(clave_documento=""),
                name="documento_unico_si_existe",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nombres} {self.apellidos}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.nacimiento is not None:
            self.anio_nacimiento = self.nacimiento.year
        super().save(*args, **kwargs)

    @property
    def nacido(self) -> Nacimiento | None:
        """El nacimiento como lo usa el dominio: completo o solo el año."""
        if self.anio_nacimiento is None:
            return None
        return Nacimiento(self.anio_nacimiento, self.nacimiento)

    @nacido.setter
    def nacido(self, valor: Nacimiento | None) -> None:
        self.anio_nacimiento = valor.anio if valor else None
        self.nacimiento = valor.fecha if valor else None


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
