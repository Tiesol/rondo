"""Formatos por cantidad de equipos (CONTEXTO 4.5; FIX-01, FIX-02 y FIX-07) como datos.

El formato de cada cantidad vive en datos/config/formatos.json: cómo se juega la fase de
grupos y qué partidos tiene la eliminación, con referencias a sus participantes ("1.º A",
"ganador de la semi 1 de Oro") que se completan cuando hay posiciones (FIX-08, P50).
"""

from dataclasses import dataclass
from pathlib import Path
from string import ascii_uppercase
from typing import Literal, Self

from pydantic import Field, model_validator

from dominio.config import Estricto

Copa = Literal["oro", "plata", "bronce"]
Ronda = Literal["semi", "final"]


class FormatoFaltante(ValueError):
    """No hay formato para esa cantidad de equipos (P27, P54)."""


class Grupos(Estricto):
    tipo: Literal["todos_contra_todos", "series_cruzadas", "series"]
    ida_y_vuelta: bool = False
    series: tuple[int, ...] = ()  # tamaños de las series A, B…; vacío en todos contra todos

    @model_validator(mode="after")
    def _series_segun_el_tipo(self) -> Self:
        if self.tipo == "todos_contra_todos" and self.series:
            raise ValueError("todos contra todos no lleva series")
        if self.tipo != "todos_contra_todos" and len(self.series) < 2:
            raise ValueError(f"{self.tipo} necesita al menos dos series")
        if self.tipo == "series_cruzadas" and len(self.series) != 2:
            raise ValueError("las series cruzadas son exactamente dos")
        return self

    @property
    def nombres_de_series(self) -> tuple[str, ...]:
        return tuple(ascii_uppercase[: len(self.series)])

    def tamanios(self, equipos: int) -> tuple[int, ...]:
        return self.series or (equipos,)

    def cantidad_de_partidos(self, equipos: int) -> int:
        if self.tipo == "todos_contra_todos":
            cruces = equipos * (equipos - 1) // 2
        elif self.tipo == "series_cruzadas":
            cruces = self.series[0] * self.series[1]
        else:
            cruces = sum(n * (n - 1) // 2 for n in self.series)
        return cruces * (2 if self.ida_y_vuelta else 1)


class Participante(Estricto):
    """Quién juega un partido de eliminación. Exactamente una de las formas."""

    puesto: int | None = Field(default=None, ge=1)
    serie: str | None = None
    ganador: str | None = None
    perdedor: str | None = None
    mejor_perdedor: tuple[str, ...] = ()
    mejor_puesto: int | None = Field(default=None, ge=1)  # el mejor de ese puesto entre series
    otro_puesto: int | None = Field(default=None, ge=1)  # el que no fue el mejor
    texto_fijo: str | None = Field(default=None, alias="texto")

    @model_validator(mode="after")
    def _una_sola_forma(self) -> Self:
        formas = [
            self.puesto is not None,
            self.ganador is not None,
            self.perdedor is not None,
            bool(self.mejor_perdedor),
            self.mejor_puesto is not None,
            self.otro_puesto is not None,
        ]
        if sum(formas) != 1:
            raise ValueError("un participante tiene exactamente una forma")
        if self.serie is not None and self.puesto is None:
            raise ValueError("la serie va solo con un puesto")
        return self

    @property
    def partidos_referidos(self) -> tuple[str, ...]:
        return tuple(p for p in (self.ganador, self.perdedor) if p) + self.mejor_perdedor

    def texto_con(self, nombres: dict[str, str]) -> str:
        """El texto para mostrar, con los nombres de los partidos a los que se refiere."""
        if self.texto_fijo:
            return self.texto_fijo
        if self.puesto is not None:
            return f"{self.puesto}.º{' ' + self.serie if self.serie else ''}"
        if self.ganador:
            return f"Ganador de la {_en_minuscula(nombres[self.ganador])}"
        if self.perdedor:
            return f"Perdedor de la {_en_minuscula(nombres[self.perdedor])}"
        if self.mejor_perdedor:
            return "Mejor perdedor de " + " y ".join(
                f"la {_en_minuscula(nombres[p])}" for p in self.mejor_perdedor
            )
        if self.mejor_puesto is not None:
            return f"Mejor {self.mejor_puesto}.º"
        return f"El otro {self.otro_puesto}.º"


def _en_minuscula(nombre: str) -> str:
    return nombre[:1].lower() + nombre[1:]


class PartidoDeEliminacion(Estricto):
    clave: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    copa: Copa
    ronda: Ronda
    local: Participante
    visitante: Participante


class Formato(Estricto):
    notas: str = ""
    grupos: Grupos
    eliminacion: tuple[PartidoDeEliminacion, ...] = ()


@dataclass(frozen=True)
class Referencia:
    """Un participante de la eliminación, con su texto para mostrar ("1.º A")."""

    participante: Participante
    texto: str


@dataclass(frozen=True)
class Llave:
    """Un partido de eliminación listo para usar: sus participantes ya tienen texto."""

    clave: str
    nombre: str
    copa: Copa
    ronda: Ronda
    local: Referencia
    visitante: Referencia


@dataclass(frozen=True)
class FormatoParaN:
    """Un formato aplicado a una cantidad de equipos."""

    equipos: int
    grupos: Grupos
    eliminacion: tuple[Llave, ...]

    @property
    def total_de_partidos(self) -> int:
        return self.grupos.cantidad_de_partidos(self.equipos) + len(self.eliminacion)


def _llaves(formato: Formato) -> tuple[Llave, ...]:
    nombres = {p.clave: p.nombre for p in formato.eliminacion}
    return tuple(
        Llave(
            p.clave,
            p.nombre,
            p.copa,
            p.ronda,
            Referencia(p.local, p.local.texto_con(nombres)),
            Referencia(p.visitante, p.visitante.texto_con(nombres)),
        )
        for p in formato.eliminacion
    )


class Formatos(Estricto):
    formatos: dict[int, Formato]
    fuente: str = Field(default="", alias="_fuente")

    @model_validator(mode="after")
    def _formatos_coherentes(self) -> Self:
        for equipos, formato in self.formatos.items():
            _validar(equipos, formato)
        return self

    def para(self, equipos: int) -> FormatoParaN:
        formato = self.formatos.get(equipos)
        if formato is None:
            raise FormatoFaltante(
                f"No hay formato para {equipos} equipos: el reglamento cubre de 3 a 10 (P27, "
                "P54). Hace falta definirlo en datos/config/formatos.json."
            )
        return FormatoParaN(equipos, formato.grupos, _llaves(formato))


def _validar(equipos: int, formato: Formato) -> None:
    grupos = formato.grupos
    if grupos.series and sum(grupos.series) != equipos:
        raise ValueError(
            f"formato de {equipos}: las series suman {sum(grupos.series)}, no {equipos}"
        )
    series = dict(zip(grupos.nombres_de_series, grupos.series, strict=True))
    tamanio_unico = None if series else equipos
    vistos: set[str] = set()
    for partido in formato.eliminacion:
        if partido.clave in vistos:
            raise ValueError(f"formato de {equipos}: la clave {partido.clave} se repite")
        for participante in (partido.local, partido.visitante):
            for referido in participante.partidos_referidos:
                if referido not in vistos:
                    raise ValueError(
                        f"formato de {equipos}: {partido.clave} se refiere a {referido}, "
                        "que no existe o viene después"
                    )
            if participante.puesto is not None:
                if participante.serie is not None and participante.serie not in series:
                    raise ValueError(
                        f"formato de {equipos}: {partido.clave} usa la serie "
                        f"{participante.serie}, que no existe"
                    )
                tope = series.get(participante.serie or "", tamanio_unico)
                if tope is None or participante.puesto > tope:
                    raise ValueError(
                        f"formato de {equipos}: {partido.clave} pide el puesto "
                        f"{participante.puesto}, que no existe"
                    )
        vistos.add(partido.clave)


def cargar_formatos(archivo: Path) -> Formatos:
    return Formatos.model_validate_json(archivo.read_text())
