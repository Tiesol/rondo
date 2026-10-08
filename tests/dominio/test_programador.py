"""PRO-01 a PRO-04 y PRO-10: el modelo CP-SAT, comprobado con el verificador."""

from datetime import datetime, timedelta
from itertools import combinations

from dominio.config import Reglas
from dominio.programador.modelo import PartidoAProgramar, Problema, Resultado, programar
from dominio.verificador import Bloqueo, Escenario, ParDeEquipos, PartidoAgendado, verificar

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
        pares=prob.pares,
        bloqueos=prob.bloqueos,
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


# ---------- T4.3: personas, bloqueos, orden y eliminación ----------


def con(prob: Problema, **cambios: object) -> Problema:
    return Problema(**{**prob.__dict__, **cambios})


def test_pro_05_dos_equipos_con_un_profe_en_comun_no_se_pisan() -> None:
    sub9 = todos_contra_todos(list("AB"), "Sub 9", ("C1",))
    sub11 = todos_contra_todos(list("CD"), "Sub 11", ("C2",))
    pares = (ParDeEquipos("Sub 9:A", "Sub 11:C", "profe"),)
    prob = con(problema(sub9 + sub11, [franja(0, 8, 10)]), pares=pares)
    resultado = programar(prob, segundos=10)
    assert resultado.sin_ubicar == []
    assert choques(prob, resultado) == []
    a, c = (resultado.ubicados[p.id][1] for p in (sub9[0], sub11[0]))
    primero, segundo = sorted((a, c))
    assert segundo - primero >= timedelta(minutes=45 + 10)


def test_pro_06_jugador_compartido() -> None:
    sub9 = todos_contra_todos(list("AB"), "Sub 9", ("C1",))
    sub11 = todos_contra_todos(list("CD"), "Sub 11", ("C2",))
    pares = (ParDeEquipos("Sub 9:A", "Sub 11:C", "jugador"),)
    prob = con(problema(sub9 + sub11, [franja(0, 8, 10)]), pares=pares)
    assert choques(prob, programar(prob, segundos=10)) == []


def test_pro_07_bloqueo_de_la_acf() -> None:
    partidos = todos_contra_todos(list("AB"))
    bloqueo = Bloqueo("Sub 9:A", SABADO.replace(hour=8), SABADO.replace(hour=11))
    prob = con(problema(partidos, [franja(0, 8, 12)]), bloqueos=(bloqueo,))
    resultado = programar(prob, segundos=10)
    assert resultado.ubicados[partidos[0].id][1] >= SABADO.replace(hour=11)
    assert choques(prob, resultado) == []


def grupo_y_llaves() -> list[PartidoAProgramar]:
    def p(id: str, equipos: tuple[str | None, str | None], **extra: object) -> PartidoAProgramar:
        return PartidoAProgramar(
            id=id,
            categoria="Sub 9",
            equipos=equipos,
            minutos_partido=45,
            minutos_turno=50,
            canchas=frozenset({"C1", "C2"}),
            **extra,  # type: ignore[arg-type]
        )

    grupos = [
        p("g1", ("A", "B"), fecha=1),
        p("g2", ("C", "D"), fecha=1),
        p("g3", ("A", "C"), fecha=2),
        p("g4", ("B", "D"), fecha=2),
        p("g5", ("A", "D"), fecha=3),
        p("g6", ("B", "C"), fecha=3),
    ]
    llaves = [
        p("s1", (None, None), fase="eliminacion", clave="oro_semi_1"),
        p("s2", (None, None), fase="eliminacion", clave="oro_semi_2"),
        p(
            "f",
            (None, None),
            fase="eliminacion",
            clave="oro_final",
            despues_de=frozenset({"oro_semi_1", "oro_semi_2"}),
        ),
    ]
    return grupos + llaves


def test_pro_08_y_pro_09_orden_de_fechas_y_eliminacion() -> None:
    partidos = grupo_y_llaves()
    franjas = [franja(d, 8, 16) for d in range(4)]
    prob = problema(partidos, franjas)
    resultado = programar(prob, segundos=15)
    assert resultado.sin_ubicar == []
    inicio = {i: resultado.ubicados[i][1] for i in resultado.ubicados}
    for equipo in "ABCD":
        suyos = sorted((p for p in partidos if equipo in p.equipos), key=lambda p: p.fecha or 0)
        horas = [inicio[p.id] for p in suyos]
        assert horas == sorted(horas), equipo
    ultimo_de_grupos = max(inicio[f"g{i}"] for i in range(1, 7))
    assert min(inicio["s1"], inicio["s2"]) >= ultimo_de_grupos + timedelta(minutes=50)
    assert inicio["f"] >= max(inicio["s1"], inicio["s2"]) + timedelta(minutes=50)
    assert choques(prob, resultado) == []


def test_pro_09_la_eliminacion_desde_su_fin_de_semana() -> None:
    partidos = grupo_y_llaves()
    franjas = [franja(d, 8, 16) for d in (0, 1, 7, 8)]
    desde = SABADO + timedelta(days=7)
    prob = con(problema(partidos, franjas), eliminacion_desde=desde)
    resultado = programar(prob, segundos=15)
    for clave in ("s1", "s2", "f"):
        assert resultado.ubicados[clave][1] >= desde


def test_una_final_sin_lugar_para_sus_semis_no_se_ubica() -> None:
    llaves = grupo_y_llaves()[6:]
    semis_imposibles = [
        PartidoAProgramar(**{**p.__dict__, "canchas": frozenset({"C9"})}) for p in llaves[:2]
    ]
    prob = problema([*semis_imposibles, llaves[2]], [franja(0, 8, 16)])
    resultado = programar(prob, segundos=10)
    assert set(resultado.sin_ubicar) == {"s1", "s2", "f"}


def test_pro_12_las_fechas_se_reparten_entre_fines_de_semana() -> None:
    partidos = grupo_y_llaves()[:6]
    franjas = [franja(d, 8, 16) for d in (0, 7, 14)]  # tres fines de semana, un día cada uno
    resultado = programar(problema(partidos, franjas), segundos=15)
    semana = {i: (resultado.ubicados[i][1] - SABADO).days // 7 for i in resultado.ubicados}
    assert {semana["g1"], semana["g2"]} == {0}
    assert {semana["g3"], semana["g4"]} == {1}
    assert {semana["g5"], semana["g6"]} == {2}
