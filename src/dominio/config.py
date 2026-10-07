"""Configuración del torneo como datos (SPEC, catálogo de reglas; CONTEXTO, secciones 4 y 9).

Ninguna regla del reglamento vive en el código: llegan en un JSON que se valida acá. Cada
regla dice de dónde sale (sección del contexto o pregunta P#).
"""

from datetime import date, time
from pathlib import Path
from typing import Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

NombreNivel = Literal["unico", "inicial", "avanzado"]
Modalidad = Literal["F5", "F7", "F8", "F11"]
DiaSemana = Literal["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
Momento = Literal["al_inscribir", "antes_del_primer_partido"]


class _Estricto(BaseModel):
    """Inmutable y sin campos desconocidos: una clave mal escrita es un error, no se ignora."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class Nivel(_Estricto):
    modalidad: Modalidad  # 4.1, P14, P15
    min: int = Field(ge=1)  # jugadores en la lista (4.1)
    max: int = Field(ge=1)
    min_por_tiempo: int = Field(gt=0)
    convocados_por_partido: int | None = Field(default=None, ge=1)  # F11: 18 de 22 (4.1)

    @model_validator(mode="after")
    def _topes_coherentes(self) -> Self:
        if self.max < self.min:
            raise ValueError(f"max ({self.max}) no puede ser menor que min ({self.min})")
        if self.convocados_por_partido is not None and self.convocados_por_partido > self.max:
            raise ValueError("convocados_por_partido no puede superar max")
        return self


class Categoria(_Estricto):
    nombre: str = Field(min_length=1)
    edad: int = Field(ge=1)  # la N de "Sub N"
    anios_nacimiento: int = Field(default=1, ge=1, le=3)  # Sub 17 abarca dos (4.1)
    genero: Literal["mixto", "F"] = "mixto"
    niveles: dict[NombreNivel, Nivel] = Field(min_length=1)

    @field_validator("niveles")
    @classmethod
    def _unico_va_solo(cls, niveles: dict[NombreNivel, Nivel]) -> dict[NombreNivel, Nivel]:
        if "unico" in niveles and len(niveles) > 1:
            raise ValueError("el nivel unico no se combina con inicial ni avanzado")
        return niveles

    def anios_de_nacimiento(self, anio_torneo: int) -> tuple[int, ...]:
        """CAT-01: año del torneo - N; Sub 17 suma el año siguiente (año - 16)."""
        primero = anio_torneo - self.edad
        return tuple(range(primero, primero + self.anios_nacimiento))


class Partido(_Estricto):
    descanso_min: int = Field(default=5, ge=0)  # 4.4
    cambio_entre_partidos_min: int = Field(default=5, ge=0)  # 4.4, P16


class Cancha(_Estricto):
    codigo: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    mitades: tuple[str, ...] = ()  # C1 se usa entera o en dos mitades (5.1)


class Compatibilidad(_Estricto):
    """Canchas por categoría (manda) o por modalidad (CAT-04)."""

    por_categoria: dict[str, tuple[str, ...]] = {}
    por_modalidad: dict[Modalidad, tuple[str, ...]] = {}


class CuerpoTecnico(_Estricto):
    max_por_equipo: int = Field(default=3, ge=1)  # 4.2, P11
    max_entrenadores: int = Field(default=1, ge=1)  # P40
    roles: tuple[str, ...] = ("entrenador", "asistente", "delegado")  # 4.2


class Torneo(_Estricto):
    nombre: str = Field(min_length=1)
    edicion: int = Field(ge=1)
    anio: int = Field(ge=2000)
    inicio: date  # P12
    fin: date
    zona_horaria: str = "America/La_Paz"

    @field_validator("zona_horaria")
    @classmethod
    def _zona_existe(cls, zona: str) -> str:
        try:
            ZoneInfo(zona)
        except ZoneInfoNotFoundError:
            raise ValueError(f"zona horaria desconocida: {zona}") from None
        return zona

    @model_validator(mode="after")
    def _fechas_en_orden(self) -> Self:
        if self.fin < self.inicio:
            raise ValueError("fin no puede ser anterior a inicio")
        return self


class Reglas(_Estricto):
    """Reglas sueltas del reglamento. El valor por defecto es el de la pregunta P# indicada."""

    jugar_en_categoria_mayor: bool = True  # P6 (INS-02)
    aviso_anios_menor: int = Field(default=2, ge=0)  # P42 (INS-02)
    jugador_en_dos_equipos: Literal["mismo_club_otra_categoria", "nunca"] = (
        "mismo_club_otra_categoria"  # P7 (INS-05)
    )
    jugador_y_profe: bool = True  # P37 (INS-07)
    dorsal_obligatorio: Momento = "antes_del_primer_partido"  # P9 (INS-09)
    ci_obligatorio: Momento = "antes_del_primer_partido"  # P39 (INS-10)
    cierre_inscripcion: date | None = None  # P4 (INS-11)
    mismo_club_fecha_1: bool = True  # P24 (FIX-05)
    sorteo_separa_clubes: bool = True  # P45 (FIX-06)
    rehacer_fixture: bool = True  # P22, P44 (FIX-09)
    turnos_libres_mismo_dia: int = Field(default=1, ge=0)  # P17 (PRO-04)
    max_partidos_por_dia: int = Field(default=2, ge=1)  # P47 (PRO-04)
    profe_minutos_cambio_de_cancha: int = Field(default=10, ge=0)  # P18, P35 (PRO-05)
    orden_de_fechas: Literal["dura", "blanda"] = "dura"  # P19 (PRO-08)
    eliminacion_desde_fin_de_semana: int = Field(default=5, ge=1)  # P33 (PRO-09)
    marcador_wo: tuple[int, int] = (3, 0)  # P23
    propuestas_reprogramacion: int = Field(default=3, ge=1, le=5)  # PRO-13


class ConfigTorneo(_Estricto):
    torneo: Torneo
    partido: Partido = Partido()
    categorias: tuple[Categoria, ...] = Field(min_length=1)
    canchas: tuple[Cancha, ...] = Field(min_length=1)
    compatibilidad: Compatibilidad
    franjas: dict[DiaSemana, tuple[time, time]]  # 4.3
    cuerpo_tecnico: CuerpoTecnico = CuerpoTecnico()
    reglas: Reglas = Reglas()

    @field_validator("franjas")
    @classmethod
    def _franjas_en_orden(
        cls, franjas: dict[DiaSemana, tuple[time, time]]
    ) -> dict[DiaSemana, tuple[time, time]]:
        for dia, (inicio, fin) in franjas.items():
            if fin <= inicio:
                raise ValueError(f"la franja del {dia} termina antes de empezar")
        return franjas

    @model_validator(mode="after")
    def _referencias_validas(self) -> Self:
        nombres = [c.nombre for c in self.categorias]
        if len(set(nombres)) != len(nombres):
            raise ValueError("hay categorías con el nombre repetido")
        codigos = {c.codigo for c in self.canchas} | {m for c in self.canchas for m in c.mitades}
        usadas = [
            *self.compatibilidad.por_categoria.values(),
            *self.compatibilidad.por_modalidad.values(),
        ]
        desconocidas = sorted({cancha for lista in usadas for cancha in lista} - codigos)
        if desconocidas:
            raise ValueError(
                f"compatibilidad con canchas que no existen: {', '.join(desconocidas)}"
            )
        sin_categoria = sorted(set(self.compatibilidad.por_categoria) - set(nombres))
        if sin_categoria:
            raise ValueError(
                f"compatibilidad con categorías que no existen: {', '.join(sin_categoria)}"
            )
        return self

    def categoria(self, nombre: str) -> Categoria:
        return next(c for c in self.categorias if c.nombre == nombre)

    def minutos_partido(self, nivel: Nivel) -> int:
        return minutos_partido(nivel.min_por_tiempo, self.partido)

    def minutos_turno(self, nivel: Nivel) -> int:
        return minutos_turno(nivel.min_por_tiempo, self.partido)


def minutos_partido(min_por_tiempo: int, partido: Partido) -> int:
    """CAT-03: dos tiempos más el descanso."""
    return 2 * min_por_tiempo + partido.descanso_min


def minutos_turno(min_por_tiempo: int, partido: Partido) -> int:
    """CAT-03: el partido más el cambio entre partidos (40, 50, 60 o 70 en 2026)."""
    return minutos_partido(min_por_tiempo, partido) + partido.cambio_entre_partidos_min


def cargar_config(archivo: Path) -> ConfigTorneo:
    return ConfigTorneo.model_validate_json(archivo.read_text())
