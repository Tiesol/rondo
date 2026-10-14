"""Reglas aflojadas solo para una reprogramación (B6, fase 12).

La organización a veces afloja una regla por un día: menos turnos libres, más partidos por día,
el orden de fechas, empezar antes o terminar después, o usar mitades de cancha. Las reglas del
torneo no cambian: esto se aplica a un problema, para una corrida, y la corrida guarda qué se
aflojó. A mano ya se puede romper cualquier regla con "Mover igual"; esto es para las
propuestas automáticas.
"""

from collections.abc import Collection
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Any

from dominio.programador.modelo import Problema
from dominio.verificador import FranjaExtra


@dataclass(frozen=True)
class Relajar:
    turnos_libres: int | None = None  # turnos libres entre partidos del mismo día
    max_por_dia: int | None = None  # máximo de partidos por equipo y día
    orden: str | None = None  # "blanda": las fechas pueden quedar al revés
    minutos_extra: int = 0  # empezar antes o terminar después, en cada franja
    usar_mitades: bool = False  # partidos de F6 y F7 también en mitades de cancha

    @property
    def vacio(self) -> bool:
        return self == Relajar()

    def a_dict(self) -> dict[str, Any]:
        por_defecto = Relajar()
        return {k: v for k, v in self.__dict__.items() if v != getattr(por_defecto, k)}

    @classmethod
    def desde_dict(cls, datos: dict[str, Any]) -> Relajar:
        return cls(**{k: v for k, v in datos.items() if k in cls.__dataclass_fields__})

    def describir(self, reglas_del_torneo: Any = None) -> list[str]:
        """Lo que se aflojó, en palabras, para la propuesta."""
        frases = []
        if self.turnos_libres is not None:
            frases.append(f"Turnos libres entre partidos del día: {self.turnos_libres}")
        if self.max_por_dia is not None:
            frases.append(f"Máximo de partidos por equipo y día: {self.max_por_dia}")
        if self.orden == "blanda":
            frases.append("Las fechas pueden quedar al revés")
        if self.minutos_extra:
            frases.append(f"Empezar hasta {self.minutos_extra} min antes o terminar después")
        if self.usar_mitades:
            frases.append("Usar mitades de cancha")
        return frases


def aplicar(
    problema: Problema,
    relajar: Relajar,
    *,
    ventana: tuple[datetime, datetime] | None = None,
    sin_mitades: Collection[str] = (),
) -> Problema:
    """El mismo problema con las reglas aflojadas. `ventana` limita dónde vale empezar antes o
    terminar después; `sin_mitades` son las categorías que no caben en media cancha (F8, F11)."""
    if relajar.vacio:
        return problema
    cambios: dict[str, Any] = {}
    if relajar.turnos_libres is not None:
        cambios["turnos_libres_mismo_dia"] = relajar.turnos_libres
    if relajar.max_por_dia is not None:
        cambios["max_partidos_por_dia"] = relajar.max_por_dia
    if relajar.orden:
        cambios["orden_de_fechas"] = relajar.orden
    nuevo = replace(problema, reglas=problema.reglas.model_copy(update=cambios))

    if relajar.minutos_extra:
        margen = timedelta(minutes=relajar.minutos_extra)
        extras = list(nuevo.extras)
        for desde, hasta in nuevo.franjas:
            if ventana is None or (desde < ventana[1] and hasta > ventana[0]):
                extras.append(FranjaExtra(desde - margen, hasta + margen))
        nuevo = replace(nuevo, extras=tuple(extras))

    if relajar.usar_mitades:
        mitades = {
            c for codigos in nuevo.fisicas.values() if len(codigos) == 1 for c in codigos
        } & {c for codigos in nuevo.fisicas.values() if len(codigos) > 1 for c in codigos}
        nuevo = replace(
            nuevo,
            partidos=tuple(
                p if p.categoria in sin_mitades else replace(p, canchas=p.canchas | mitades)
                for p in nuevo.partidos
            ),
        )
    return nuevo
