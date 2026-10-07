"""Configuración del torneo en la base (T1.3). Las reglas se validan con dominio.config."""

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from pydantic import BaseModel
from pydantic import ValidationError as ErrorDePydantic

from dominio.config import CuerpoTecnico, Partido, Reglas, minutos_partido, minutos_turno


def _validar_con(esquema: type[BaseModel], valor: Any) -> dict[str, Any]:
    """Valida un JSON con un esquema del dominio y lo devuelve con los valores por defecto."""
    try:
        return esquema.model_validate(valor).model_dump(mode="json")
    except ErrorDePydantic as error:
        mensajes = [
            f"{'.'.join(str(parte) for parte in e['loc']) or 'valor'}: {e['msg']}"
            for e in error.errors()
        ]
        raise ValidationError(mensajes) from None


def _reglas_por_defecto() -> dict[str, Any]:
    return Reglas().model_dump(mode="json")


def _cuerpo_tecnico_por_defecto() -> dict[str, Any]:
    return CuerpoTecnico().model_dump(mode="json")


class Torneo(models.Model):
    nombre = models.CharField(max_length=100)
    edicion = models.PositiveSmallIntegerField()
    anio = models.PositiveSmallIntegerField("año")
    inicio = models.DateField()
    fin = models.DateField()
    zona_horaria = models.CharField(max_length=50, default="America/La_Paz")
    descanso_min = models.PositiveSmallIntegerField("descanso (min)", default=5)
    cambio_entre_partidos_min = models.PositiveSmallIntegerField(
        "cambio entre partidos (min)", default=5
    )
    cuerpo_tecnico = models.JSONField(default=_cuerpo_tecnico_por_defecto)
    reglas = models.JSONField(default=_reglas_por_defecto)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fin__gte=models.F("inicio")), name="torneo_fin_despues_de_inicio"
            ),
            # cargar_config reconoce al torneo por nombre y año.
            models.UniqueConstraint(fields=["nombre", "anio"], name="torneo_unico_por_anio"),
        ]

    def __str__(self) -> str:
        return self.nombre

    def save(self, *args: Any, **kwargs: Any) -> None:
        # Se valida siempre, también fuera del admin: unas reglas inválidas nunca llegan a la base.
        self.clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        self.reglas = _validar_con(Reglas, self.reglas)
        self.cuerpo_tecnico = _validar_con(CuerpoTecnico, self.cuerpo_tecnico)

    @property
    def partido(self) -> Partido:
        return Partido(
            descanso_min=self.descanso_min,
            cambio_entre_partidos_min=self.cambio_entre_partidos_min,
        )


class CategoriaNivel(models.Model):
    """La unidad de competencia, por ejemplo "Sub 9 Inicial" (ARQUITECTURA, sección 6)."""

    class Nivel(models.TextChoices):
        UNICO = "unico", "Único"
        INICIAL = "inicial", "Inicial"
        AVANZADO = "avanzado", "Avanzado"

    class Modalidad(models.TextChoices):
        F5 = "F5", "Fútbol 5"
        F7 = "F7", "Fútbol 7"
        F8 = "F8", "Fútbol 8"
        F11 = "F11", "Fútbol 11"

    class Genero(models.TextChoices):
        MIXTO = "mixto", "Mixto"
        FEMENINO = "F", "Femenino"

    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name="categorias")
    categoria = models.CharField(max_length=50)
    edad = models.PositiveSmallIntegerField(help_text="La N de «Sub N»")
    anios_nacimiento = models.PositiveSmallIntegerField("años de nacimiento", default=1)
    genero = models.CharField(max_length=5, choices=Genero.choices, default=Genero.MIXTO)
    nivel = models.CharField(max_length=10, choices=Nivel.choices)
    modalidad = models.CharField(max_length=3, choices=Modalidad.choices)
    min_jugadores = models.PositiveSmallIntegerField("mínimo de jugadores")
    max_jugadores = models.PositiveSmallIntegerField("máximo de jugadores")
    min_por_tiempo = models.PositiveSmallIntegerField("minutos por tiempo")
    convocados_por_partido = models.PositiveSmallIntegerField(null=True, blank=True)
    canchas: models.ManyToManyField[Cancha, Any] = models.ManyToManyField(
        "Cancha", blank=True, related_name="categorias", verbose_name="canchas compatibles"
    )

    class Meta:
        verbose_name = "categoría-nivel"
        verbose_name_plural = "categorías-nivel"
        ordering = ["torneo", "edad", "categoria", "nivel"]
        constraints = [
            models.UniqueConstraint(
                fields=["torneo", "categoria", "nivel"], name="categoria_nivel_unica"
            ),
            models.CheckConstraint(
                condition=models.Q(max_jugadores__gte=models.F("min_jugadores")),
                name="max_jugadores_no_menor_que_min",
            ),
        ]

    def __str__(self) -> str:
        if self.nivel == self.Nivel.UNICO:
            return self.categoria
        return f"{self.categoria} {self.get_nivel_display()}"

    @property
    def minutos_partido(self) -> int:
        return minutos_partido(self.min_por_tiempo, self.torneo.partido)

    @property
    def minutos_turno(self) -> int:
        return minutos_turno(self.min_por_tiempo, self.torneo.partido)


class Cancha(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name="canchas")
    codigo = models.CharField(max_length=10)
    nombre = models.CharField(max_length=50)
    padre = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="mitades",
        help_text="Si es la mitad de otra cancha. La cancha entera ocupa sus mitades.",
    )

    class Meta:
        ordering = ["torneo", "codigo"]
        constraints = [
            models.UniqueConstraint(fields=["torneo", "codigo"], name="codigo_de_cancha_unico")
        ]

    def __str__(self) -> str:
        return self.codigo


class Franja(models.Model):
    class Tipo(models.TextChoices):
        REGULAR = "regular", "Regular"
        ENTRE_SEMANA = "entre_semana", "Entre semana (para reprogramar)"

    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name="franjas")
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    tipo = models.CharField(max_length=12, choices=Tipo.choices, default=Tipo.REGULAR)

    class Meta:
        ordering = ["torneo", "inicio"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fin__gt=models.F("inicio")), name="franja_fin_despues_de_inicio"
            )
        ]

    def __str__(self) -> str:
        inicio, fin = timezone.localtime(self.inicio), timezone.localtime(self.fin)
        return f"{inicio:%Y-%m-%d %H:%M} a {fin:%H:%M}"
