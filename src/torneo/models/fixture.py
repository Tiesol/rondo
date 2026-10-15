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
        EN_JUEGO = "en_juego", "En juego"  # T8.5: ya no se mueve
        JUGADO = "jugado", "Jugado"

    class Tiempo(models.TextChoices):
        SIN_EMPEZAR = "", "Sin empezar"
        PRIMER_TIEMPO = "primer_tiempo", "1.er tiempo"
        DESCANSO = "descanso", "Descanso"
        SEGUNDO_TIEMPO = "segundo_tiempo", "2.º tiempo"
        TERMINADO = "terminado", "Terminado"

    class Lado(models.TextChoices):
        LOCAL = "local", "Local"
        VISITANTE = "visitante", "Visitante"

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
    # Resultado (T8.5): el marcador sale de los eventos; esto es lo que no sale de ahí.
    no_se_presento = models.CharField(max_length=9, choices=Lado.choices, blank=True)  # W.O.
    penales_local = models.PositiveSmallIntegerField(null=True, blank=True)
    penales_visitante = models.PositiveSmallIntegerField(null=True, blank=True)
    # T10.9: los tiempos los marca la mesa a mano (el partido puede empezar tarde).
    tiempo = models.CharField(max_length=14, choices=Tiempo.choices, blank=True)
    inicio_real = models.DateTimeField(null=True, blank=True)
    fin_primer_tiempo = models.DateTimeField(null=True, blank=True)
    fin_descanso = models.DateTimeField(null=True, blank=True)
    fin_real = models.DateTimeField(null=True, blank=True)
    # T11.12: se cerró solo porque nadie lo terminó (P82); queda marcado para revisar.
    cerrado_automaticamente = models.BooleanField(default=False)
    # T13.21: decisión explícita de la organización. Nada automático lo mueve (programar,
    # rehacer el fixture ni las propuestas); se mueve solo a mano. Mover no fija solo.
    fijado = models.BooleanField(default=False)
    # T11.8: si el entrenador de cada equipo estuvo (opcional; vacío, sin marcar).
    entrenador_local = models.BooleanField(null=True, blank=True)
    entrenador_visitante = models.BooleanField(null=True, blank=True)
    mejor_jugador = models.ForeignKey(
        "Jugador", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )  # P70

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

    @property
    def empezado(self) -> bool:
        """En juego o jugado: ya no se mueve ni se rehace su fixture (PRO-10, FIX-09)."""
        return self.estado in (self.Estado.EN_JUEGO, self.Estado.JUGADO)
