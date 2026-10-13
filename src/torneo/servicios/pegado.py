"""Cargar una lista pegada (T7.8 y T7.9): cada fila pasa por la misma carga que a mano.

La vista previa es la misma carga dentro de una transacción que se deshace al final. Así
muestra exactamente lo que pasaría al guardar, incluido lo que depende de la lista entera
(un dorsal repetido, el plantel que se llena).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from django.db import transaction

from dominio.inscripcion import Hallazgo
from dominio.pegado import FilaLeida
from torneo.models import Equipo
from torneo.servicios.inscripcion import DatosPersona, agregar_jugador, agregar_profe

Que = Literal["jugadores", "profes"]
MAX_FILAS = 60  # un plantel de F11 tiene 22: más es otra lista pegada por error


@dataclass
class FilaCargada:
    numero: int
    campos: dict[str, str]  # el texto de cada campo, para mostrarlo y corregirlo
    hallazgos: list[Hallazgo] = field(default_factory=list)
    guardada: bool = False  # en la vista previa: se guardaría

    @property
    def errores(self) -> list[Hallazgo]:
        return [h for h in self.hallazgos if h.nivel == "error"]

    @property
    def avisos(self) -> list[Hallazgo]:
        return [h for h in self.hallazgos if h.nivel == "aviso"]


def editables(fila: FilaLeida, campos: dict[str, str]) -> dict[str, str]:
    """Los campos como se van a mostrar para corregir: lo que se entendió, ya normalizado
    (una fecha en mm/dd queda en dd/mm); lo que no, como vino."""
    return {
        "nombres": fila.nombres,
        "apellidos": fila.apellidos,
        "nacimiento": str(fila.nacimiento) if fila.nacimiento else campos.get("nacimiento", ""),
        "documento": fila.documento,
        "dorsal": str(fila.dorsal) if fila.dorsal is not None else campos.get("dorsal", ""),
        "rol": fila.rol or campos.get("rol", ""),
    }


def cargar_lista(
    equipo: Equipo,
    filas: Sequence[tuple[FilaLeida, dict[str, str]]],
    que: Que,
    *,
    ahora: datetime,
    es_organizacion: bool,
    guardar: bool,
    roles: Sequence[str],
) -> list[FilaCargada]:
    """Carga las filas sin errores, en orden. Cada fila va con el texto de sus campos, para
    volver a mostrarla. Sin `guardar`, no queda nada en la base."""
    cargadas = []
    with transaction.atomic():
        for fila, campos in filas:
            cargada = FilaCargada(fila.numero, editables(fila, campos))
            cargadas.append(cargada)
            if fila.errores:
                cargada.hallazgos = [Hallazgo("error", "", e) for e in fila.errores]
                continue
            datos = DatosPersona(fila.documento, fila.nombres, fila.apellidos, fila.nacimiento)
            if que == "jugadores":
                resultado = agregar_jugador(
                    equipo, datos, fila.dorsal, ahora=ahora, es_organizacion=es_organizacion
                )
            elif fila.rol is None:
                faltan = ", ".join(roles)
                cargada.hallazgos = [Hallazgo("error", "INS-08", f"Falta el rol: {faltan}.")]
                continue
            else:
                resultado = agregar_profe(
                    equipo, datos, fila.rol, ahora=ahora, es_organizacion=es_organizacion
                )
            # "Faltan N para el mínimo" en cada fila no ayuda: la ficha muestra cuántos faltan.
            cargada.hallazgos = [
                h for h in resultado.hallazgos if (h.nivel, h.regla) != ("aviso", "INS-03")
            ]
            cargada.guardada = resultado.guardado
        if not guardar:
            transaction.set_rollback(True)
    return cargadas
