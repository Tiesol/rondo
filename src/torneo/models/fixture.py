"""Fixture: series y partidos (ARQUITECTURA, sección 6; FIX-08 y FIX-09)."""

from django.db import models

from torneo.models.configuracion import Cancha, CategoriaNivel
from torneo.models.inscripcion import Equipo


class Serie(models.Model):
    categoria = models.ForeignKey(CategoriaNivel, on_delete=models.CASCADE, related_name="series")
    nombre = models.CharField(max_length=2)
    equipos = models.ManyToManyField(Equipo, related_name="series")

    class Meta:
        ordering = ["categoria", "nombre"]
        constraints = [models.UniqueConstraint(fields=["categoria", "nombre"], name="serie_unica")]

    def __str__(self) -> str:
        return f"Serie {self.nombre} ({self.categoria})"


class Partido(models.Model):
    """Un partido del fixture. En la eliminación, los participantes pueden estar por definir:
    local y visitante vacíos, con su referencia en texto ("1.º A") hasta que se asignen (P50)."""

    class Fase(models.TextChoices):
        GRUPOS = "grupos", "Fase de grupos"
        ELIMINACION = "eliminacion", "Eliminación"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Sin programar"
        PROGRAMADO = "programado", "Programado"
        JUGADO = "jugado", "Jugado"

    categoria = models.ForeignKey(CategoriaNivel, on_delete=models.CASCADE, related_name="partidos")
    fase = models.CharField(max_length=11, choices=Fase.choices)
    copa = models.CharField(max_length=6, blank=True)  # oro, plata o bronce
    ronda = models.CharField(max_length=5, blank=True)  # semi o final
    clave = models.CharField(max_length=30, blank=True)  # en la eliminación: "oro_semi_1"
    nombre = models.CharField(max_length=60, blank=True)  # "Semi 1 de Oro"
    fecha = models.PositiveSmallIntegerField(null=True, blank=True)  # en la fase de grupos
    serie = models.ForeignKey(
        Serie, on_delete=models.SET_NULL, null=True, blank=True, related_name="partidos"
    )
    local = models.ForeignKey(
        Equipo, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    visitante = models.ForeignKey(
        Equipo, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    texto_local = models.CharField(max_length=80, blank=True)
    texto_visitante = models.CharField(max_length=80, blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    cancha = models.ForeignKey(
        Cancha, on_delete=models.SET_NULL, null=True, blank=True, related_name="partidos"
    )
    inicio = models.DateTimeField(null=True, blank=True)
    fijado = models.BooleanField(default=False, help_text="Fijado a mano: no se mueve (PRO-10)")

    class Meta:
        ordering = ["categoria", "fase", "fecha", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(local=models.F("visitante"))
                | models.Q(local__isnull=True)
                | models.Q(visitante__isnull=True),
                name="local_distinto_de_visitante",
            ),
            models.UniqueConstraint(
                fields=["categoria", "clave"],
                condition=~models.Q(clave=""),
                name="clave_de_partido_unica",
            ),
        ]

    def __str__(self) -> str:
        local = self.local.nombre if self.local else self.texto_local
        visitante = self.visitante.nombre if self.visitante else self.texto_visitante
        return f"{local} vs {visitante} ({self.categoria})"
