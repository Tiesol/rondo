"""El asistente para crear un torneo (TU.4): de las respuestas de cada paso a la configuración.

Las respuestas se guardan aparte de la plantilla, así volver a un paso muestra lo elegido y
destildar y volver a tildar una categoría no pierde nada. La configuración final se arma
recién al terminar, y se valida con el dominio como cualquier JSON.
"""

import json
from copy import deepcopy
from datetime import date
from typing import Any

from django.conf import settings

from dominio.config import Categoria, ConfigTorneo

DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
NOMBRE_DEL_DIA = {
    "lunes": "Lunes",
    "martes": "Martes",
    "miercoles": "Miércoles",
    "jueves": "Jueves",
    "viernes": "Viernes",
    "sabado": "Sábado",
    "domingo": "Domingo",
}
NOMBRE_DEL_NIVEL = {"unico": "", "inicial": "Inicial", "avanzado": "Avanzado"}

Respuestas = dict[str, Any]


def plantilla() -> dict[str, Any]:
    datos: dict[str, Any] = json.loads(settings.PLANTILLA_TORNEO.read_text())
    return datos


def clave_del_nivel(categoria: str, nivel: str) -> str:
    return f"{categoria}|{nivel}"


def niveles_de(config: dict[str, Any]) -> list[dict[str, str]]:
    """Las categorías-nivel de la plantilla, con lo que se muestra en el paso 2."""
    anio = date.fromisoformat(config["torneo"]["inicio"]).year
    niveles = []
    for datos in config["categorias"]:
        categoria = Categoria.model_validate(datos)
        nacidos = " o ".join(str(a) for a in categoria.anios_de_nacimiento(anio))
        for nombre_nivel, nivel in categoria.niveles.items():
            niveles.append(
                {
                    "clave": clave_del_nivel(categoria.nombre, nombre_nivel),
                    "titulo": f"{categoria.nombre} {NOMBRE_DEL_NIVEL[nombre_nivel]}".strip(),
                    "sub": f"{nivel.modalidad} · {nivel.min} a {nivel.max} jugadores · "
                    f"nacidos en {nacidos}",
                }
            )
    return niveles


def armar(base: dict[str, Any], respuestas: Respuestas) -> ConfigTorneo:
    """La plantilla con las respuestas aplicadas, validada por el dominio."""
    config = deepcopy(base)
    if datos := respuestas.get("datos"):
        config["torneo"] |= {
            "nombre": datos["nombre"],
            "edicion": datos["edicion"],
            "inicio": datos["inicio"],
            "fin": datos["fin"],
            "anio": date.fromisoformat(datos["inicio"]).year,
        }
    if (elegidos := respuestas.get("niveles")) is not None:
        categorias = []
        for categoria in config["categorias"]:
            niveles = {
                nombre: nivel
                for nombre, nivel in categoria["niveles"].items()
                if clave_del_nivel(categoria["nombre"], nombre) in elegidos
            }
            if niveles:
                categorias.append(categoria | {"niveles": niveles})
        config["categorias"] = categorias
        quedan = {c["nombre"] for c in categorias}
        por_categoria = config["compatibilidad"].get("por_categoria", {})
        config["compatibilidad"]["por_categoria"] = {
            nombre: canchas for nombre, canchas in por_categoria.items() if nombre in quedan
        }
    if (franjas := respuestas.get("franjas")) is not None:
        config["franjas"] = franjas
    if (reglas := respuestas.get("reglas")) is not None:
        config["reglas"] = reglas
    return ConfigTorneo.model_validate(config)
