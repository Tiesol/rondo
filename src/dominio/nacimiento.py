"""Fecha de nacimiento: completa o solo el año (pedido 2026, A3).

La regla de edad (INS-02) mira solo el año, así que alcanza con él. En las listas reales de
2023, 3 listas traían solo el año: eso es una fecha incompleta, no un error.
"""

import re
from dataclasses import dataclass
from datetime import date

ANIO_MINIMO = 1900  # nadie inscrito nació antes; filtra un "14" o un número suelto


class NacimientoInvalido(ValueError):
    """El texto no es una fecha de nacimiento que se entienda."""


@dataclass(frozen=True, slots=True)
class Nacimiento:
    anio: int
    fecha: date | None = None  # la fecha completa, si se conoce

    def __post_init__(self) -> None:
        if self.fecha is not None and self.fecha.year != self.anio:
            raise ValueError(f"la fecha {self.fecha} no es del año {self.anio}")

    @classmethod
    def de(cls, fecha: date) -> Nacimiento:
        return cls(fecha.year, fecha)

    @property
    def completa(self) -> bool:
        return self.fecha is not None

    def __str__(self) -> str:
        return f"{self.fecha:%d/%m/%Y}" if self.fecha else str(self.anio)


_EJEMPLOS = "Escribe la fecha como dd/mm/aaaa (12/03/2014) o solo el año (2014)."
_DMA = re.compile(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})")
_ISO = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")


def _fecha(anio: int, mes: int, dia: int, texto: str) -> Nacimiento:
    if anio < ANIO_MINIMO:
        raise NacimientoInvalido(f"«{texto}» no es una fecha de nacimiento. {_EJEMPLOS}")
    try:
        return Nacimiento.de(date(anio, mes, dia))
    except ValueError:
        raise NacimientoInvalido(f"«{texto}» no es una fecha que exista. {_EJEMPLOS}") from None


def leer_nacimiento(texto: str) -> Nacimiento:
    """dd/mm/aaaa (con /, - o .), aaaa-mm-dd o solo el año."""
    limpio = texto.strip()
    if m := _DMA.fullmatch(limpio):
        return _fecha(int(m[3]), int(m[2]), int(m[1]), limpio)
    if m := _ISO.fullmatch(limpio):
        return _fecha(int(m[1]), int(m[2]), int(m[3]), limpio)
    if re.fullmatch(r"\d{4}", limpio) and int(limpio) >= ANIO_MINIMO:
        return Nacimiento(int(limpio))
    raise NacimientoInvalido(
        f"«{limpio}» no es una fecha de nacimiento. {_EJEMPLOS}"
        if limpio
        else f"Falta la fecha de nacimiento. {_EJEMPLOS}"
    )
