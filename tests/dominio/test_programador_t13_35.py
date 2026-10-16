"""T13.35: con poca CPU el solver puede no encontrar nada. La pista del calendario actual y
los motivos que cortan rápido."""

import time
from dataclasses import replace
from datetime import datetime, timedelta
from itertools import combinations

import pytest

from dominio.config import Reglas
from dominio.programador.modelo import Modelo, PartidoAProgramar, Problema, Resultado, programar
from dominio.programador.motivos import motivos_sin_ubicar

FISICAS = {"C1": frozenset({"C1"}), "C2": frozenset({"C2"})}
SABADO = datetime(2026, 10, 24)


def franja(dia: int, desde: int, hasta: int) -> tuple[datetime, datetime]:
    base = SABADO + timedelta(days=dia)
    return base.replace(hour=desde), base.replace(hour=hasta)


def todos_contra_todos(
    equipos: list[str], canchas: tuple[str, ...] = ("C1", "C2")
) -> list[PartidoAProgramar]:
    return [
        PartidoAProgramar(
            id=f"{a}-{b}",
            categoria="Sub 9",
            equipos=(a, b),
            minutos_partido=45,
            minutos_turno=50,
            canchas=frozenset(canchas),
        )
        for a, b in combinations(equipos, 2)
    ]


def problema(
    partidos: list[PartidoAProgramar], franjas: list[tuple[datetime, datetime]]
) -> Problema:
    return Problema(
        partidos=tuple(partidos), fisicas=FISICAS, franjas=tuple(franjas), reglas=Reglas()
    )


def _modelo(prob: Problema) -> Modelo:
    modelo = Modelo(prob)
    modelo.variables()
    modelo.pistas()
    return modelo


def test_el_calendario_actual_va_como_pista_al_solver() -> None:
    partidos = todos_contra_todos(["A", "B", "C", "D"])
    prob = problema(partidos, [franja(0, 8, 18), franja(1, 8, 18)])
    resultado = programar(prob, segundos=5, trabajadores=1)
    assert not resultado.sin_ubicar
    con_pista = replace(
        prob, partidos=tuple(replace(p, pista=resultado.ubicados[p.id]) for p in prob.partidos)
    )

    sugeridas = len(_modelo(con_pista).modelo.proto.solution_hint.vars)
    sin_pista = len(_modelo(prob).modelo.proto.solution_hint.vars)

    assert sin_pista == 0
    assert sugeridas >= 3 * len(partidos)  # presente, inicio y cancha de cada uno


def test_una_pista_que_ya_no_vale_se_ignora() -> None:
    """Por ejemplo, el partido estaba en una cancha que su categoría ya no usa."""
    (partido,) = todos_contra_todos(["A", "B"], canchas=("C2",))
    con_pista = replace(partido, pista=("C1", franja(0, 8, 18)[0]))
    prob = problema([con_pista], [franja(0, 8, 18)])
    assert len(_modelo(prob).modelo.proto.solution_hint.vars) == 0
    assert programar(prob, segundos=5, trabajadores=1).ubicados


def test_los_motivos_cortan_al_encontrar_un_lugar_libre() -> None:
    """Sin solución quedan todos sin ubicar; con 0,1 CPU los motivos tardaban más que el
    solver porque probaban todos los inicios aunque el primero ya estaba libre."""
    partidos = todos_contra_todos([f"E{i}" for i in range(14)])  # 91 partidos
    franjas = [franja(d, 8, 20) for d in range(0, 21)]
    prob = problema(partidos, franjas)
    vacio = Resultado(sin_ubicar=[p.id for p in partidos], estado="UNKNOWN")

    comienzo = time.monotonic()
    motivos = motivos_sin_ubicar(prob, vacio)

    assert time.monotonic() - comienzo < 1
    assert set(motivos.values()) == {
        "Hay lugar, pero el programador no llegó a ubicarlo en el tiempo dado"
    }


def test_con_poca_cpu_una_sola_pasada_con_todo_el_tiempo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Con orden "blanda" se resuelve dos veces con la mitad del tiempo cada una (A2). Con 0,1
    CPU, partir el tiempo deja todo sin ubicar: una sola pasada, la blanda, con todo."""
    from dominio.programador import modelo

    llamadas: list[tuple[str, float]] = []
    original = modelo._resolver

    def espiar(prob: Problema, segundos: float, trabajadores: int, semilla: int) -> Resultado:
        llamadas.append((prob.reglas.orden_de_fechas, segundos))
        return original(prob, segundos, trabajadores, semilla)

    monkeypatch.setattr(modelo, "_resolver", espiar)
    prob = replace(
        problema(todos_contra_todos(["A", "B", "C"]), [franja(0, 8, 18)]),
        reglas=Reglas(orden_de_fechas="blanda"),
    )
    programar(prob, segundos=4, trabajadores=1, una_pasada=True)
    assert llamadas == [("blanda", 4)]
