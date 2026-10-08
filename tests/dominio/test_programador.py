"""PRO-01 a PRO-04 y PRO-10: el modelo CP-SAT, comprobado con el verificador."""

from datetime import datetime, timedelta
from itertools import combinations

from dominio.config import Reglas
from dominio.programador.modelo import PartidoAProgramar, Problema, Resultado, programar
from dominio.verificador import Escenario, PartidoAgendado, verificar

FISICAS = {
    c: frozenset(u)
    for c, u in {"C1": {"C1A", "C1B"}, "C1A": {"C1A"}, "C1B": {"C1B"}, "C2": {"C2"}}.items()
}
SABADO = datetime(2026, 10, 24)


def franja(dia: int, desde: int, hasta: int) -> tuple[datetime, datetime]:
    base = SABADO + timedelta(days=dia)
    return base.replace(hour=desde), base.replace(hour=hasta)


def todos_contra_todos(
    equipos: list[str],
    categoria: str = "Sub 9",
    canchas: tuple[str, ...] = ("C1", "C2"),
    turno: int = 50,
) -> list[PartidoAProgramar]:
    return [
        PartidoAProgramar(
            id=f"{categoria}:{a}-{b}",
            categoria=categoria,
            equipos=(f"{categoria}:{a}", f"{categoria}:{b}"),
            minutos_partido=turno - 5,
            minutos_turno=turno,
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


def choques(prob: Problema, resultado: Resultado) -> list[str]:
    agendados = [
        PartidoAgendado(
            id=p.id,
            categoria=p.categoria,
            equipos=p.equipos,
            cancha=resultado.ubicados[p.id][0],
            inicio=resultado.ubicados[p.id][1],
            minutos_partido=p.minutos_partido,
            minutos_turno=p.minutos_turno,
        )
        for p in prob.partidos
        if p.id in resultado.ubicados
    ]
    escenario = Escenario(
        fisicas=prob.fisicas,
        compatibilidad={p.categoria: p.canchas for p in prob.partidos},
        franjas=prob.franjas,
        pares=(),
        bloqueos=(),
        reglas=prob.reglas,
    )
    return [f"{c.tipo}: {c.motivos}" for c in verificar(agendados, escenario)]


def test_un_caso_chico_entra_entero_y_sin_choques() -> None:
    prob = problema(todos_contra_todos(list("ABCD")), [franja(0, 8, 12), franja(1, 8, 12)])
    resultado = programar(prob, segundos=10)
    assert resultado.sin_ubicar == []
    assert len(resultado.ubicados) == 6
    assert choques(prob, resultado) == []


def test_si_no_entra_todo_lo_que_queda_afuera_no_rompe_nada() -> None:
    # 15 partidos y lugar para pocos: una sola cancha y dos horas.
    prob = problema(todos_contra_todos(list("ABCDEF"), canchas=("C2",)), [franja(0, 8, 10)])
    resultado = programar(prob, segundos=10)
    assert 0 < len(resultado.ubicados) <= 2
    assert len(resultado.sin_ubicar) == 15 - len(resultado.ubicados)
    assert choques(prob, resultado) == []


def test_las_mitades_y_la_cancha_entera_no_se_pisan() -> None:
    enteras = todos_contra_todos(list("ABC"), "Sub 9", ("C1",))
    mitades = todos_contra_todos(list("DEFG"), "Sub 6", ("C1A", "C1B"), turno=40)
    # Dos días: con 4 equipos, cada uno juega 3 partidos y el máximo por día es 2.
    prob = problema(enteras + mitades, [franja(0, 8, 14), franja(1, 8, 14)])
    resultado = programar(prob, segundos=10)
    assert resultado.sin_ubicar == []
    assert choques(prob, resultado) == []


def test_pro_04_maximo_por_dia_y_turno_libre() -> None:
    # A juega 3 partidos y el máximo por día es 2: hacen falta dos días.
    prob = problema(todos_contra_todos(list("ABCD")), [franja(0, 8, 16), franja(1, 8, 16)])
    resultado = programar(prob, segundos=10)
    assert resultado.sin_ubicar == []
    por_dia: dict[tuple[str, object], int] = {}
    for partido in prob.partidos:
        dia = resultado.ubicados[partido.id][1].date()
        for equipo in partido.equipos:
            por_dia[(str(equipo), dia)] = por_dia.get((str(equipo), dia), 0) + 1
    assert max(por_dia.values()) <= 2
    assert choques(prob, resultado) == []


def test_pro_10_un_partido_fijado_no_se_mueve() -> None:
    partidos = todos_contra_todos(list("ABC"))
    fijo = SABADO.replace(hour=11, minute=10)
    partidos[0] = PartidoAProgramar(**{**partidos[0].__dict__, "fijo": ("C2", fijo)})
    prob = problema(partidos, [franja(0, 8, 14), franja(1, 8, 14)])
    resultado = programar(prob, segundos=10)
    assert resultado.ubicados[partidos[0].id] == ("C2", fijo)
    assert choques(prob, resultado) == []


def test_los_partidos_terminan_dentro_de_su_franja() -> None:
    prob = problema(todos_contra_todos(list("AB")), [franja(0, 8, 9)])
    resultado = programar(prob, segundos=5)
    _, inicio = resultado.ubicados["Sub 9:A-B"]
    assert inicio + timedelta(minutes=45) <= SABADO.replace(hour=9)
    assert inicio.minute % 5 == 0
