"""Equipos que no pueden jugar a la vez porque comparten a una persona (ARQUITECTURA 6).

No se guardan: se calculan desde Persona cuando hacen falta. Al dominio le llegan solo
identificadores de equipo y el motivo, nunca nombres ni documentos.
"""

from collections import defaultdict
from itertools import combinations
from typing import Literal

from dominio.config import Reglas
from dominio.verificador import ParDeEquipos
from torneo.models import Jugador, Profe, Torneo

Rol = Literal["jugador", "profe"]


def pares_de_equipos(torneo: Torneo) -> list[ParDeEquipos]:
    """Un par por persona y par de equipos en los que tiene que estar. "jugador" si en los
    dos juega; si dirige en alguno, "profe" (necesita además el margen para cambiar de
    cancha, P35). Del cuerpo técnico, por defecto cuenta solo el entrenador: es el único que
    entra a la cancha a dirigir (P57)."""
    solo_entrenador = Reglas.model_validate(torneo.reglas).choque_de_profes == "entrenador"
    roles: dict[int, dict[int, set[Rol]]] = defaultdict(lambda: defaultdict(set))
    for persona, equipo in Jugador.objects.filter(equipo__categoria__torneo=torneo).values_list(
        "persona_id", "equipo_id"
    ):
        roles[persona][equipo].add("jugador")
    profes = Profe.objects.filter(equipo__categoria__torneo=torneo)
    if solo_entrenador:
        profes = profes.filter(rol="entrenador")
    for persona, equipo in profes.values_list("persona_id", "equipo_id"):
        roles[persona][equipo].add("profe")

    pares = []
    for por_equipo in roles.values():
        for a, b in combinations(sorted(por_equipo), 2):
            solo_juega = por_equipo[a] == por_equipo[b] == {"jugador"}
            pares.append(ParDeEquipos(a, b, "jugador" if solo_juega else "profe"))
    return pares
