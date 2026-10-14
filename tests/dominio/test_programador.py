"""PRO-01 a PRO-04 y PRO-10: el modelo CP-SAT, comprobado con el verificador."""

from datetime import datetime, timedelta
from itertools import combinations, pairwise

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
        extras=prob.extras,
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


def test_t7_2_un_profe_compartido_puede_tener_partidos_seguidos_en_la_misma_cancha() -> None:
    # P18 y CONTEXTO 6.4: seguidos en la misma cancha está bien (5 min entre uno y otro).
    sub9 = todos_contra_todos(list("AB"), "Sub 9", ("C1",))
    sub11 = todos_contra_todos(list("CD"), "Sub 11", ("C1",))
    pares = (ParDeEquipos("Sub 9:A", "Sub 11:C", "profe"),)
    justa = SABADO.replace(hour=8), SABADO.replace(hour=9, minute=35)  # dos turnos y nada más
    prob = con(problema(sub9 + sub11, [justa]), pares=pares)
    resultado = programar(prob, segundos=10)
    assert resultado.sin_ubicar == []
    assert choques(prob, resultado) == []


def test_t7_2_en_canchas_distintas_necesita_el_margen() -> None:
    sub9 = todos_contra_todos(list("AB"), "Sub 9", ("C1",))
    sub11 = todos_contra_todos(list("CD"), "Sub 11", ("C2",))
    pares = (ParDeEquipos("Sub 9:A", "Sub 11:C", "profe"),)
    justa = SABADO.replace(hour=8), SABADO.replace(hour=9, minute=35)
    prob = con(problema(sub9 + sub11, [justa]), pares=pares)
    resultado = programar(prob, segundos=10)
    assert len(resultado.sin_ubicar) == 1  # 45 + 10 + 45 no entra en 95 minutos
    assert choques(prob, resultado) == []


def test_t7_2_un_jugador_compartido_no_necesita_margen() -> None:
    sub9 = todos_contra_todos(list("AB"), "Sub 9", ("C1",))
    sub11 = todos_contra_todos(list("CD"), "Sub 11", ("C2",))
    pares = (ParDeEquipos("Sub 9:A", "Sub 11:C", "jugador"),)
    justa = SABADO.replace(hour=8), SABADO.replace(hour=9, minute=35)
    resultado = programar(con(problema(sub9 + sub11, [justa]), pares=pares), segundos=10)
    assert resultado.sin_ubicar == []


def test_t7_3_pro_11_con_lugar_libre_los_partidos_del_profe_van_seguidos() -> None:
    sub9 = todos_contra_todos(list("AB"), "Sub 9", ("C1",))
    fijo = (("C2", SABADO.replace(hour=14)),)
    sub11 = [
        PartidoAProgramar(**{**p.__dict__, "fijo": fijo[0]})
        for p in todos_contra_todos(list("CD"), "Sub 11", ("C2",))
    ]
    pares = (ParDeEquipos("Sub 9:A", "Sub 11:C", "profe"),)
    prob = con(problema(sub9 + sub11, [franja(0, 8, 16)]), pares=pares)
    sub9_inicio = programar(prob, segundos=10).ubicados[sub9[0].id][1]
    # Pegado al de las 14:00: 10 minutos de margen antes (13:05) o después (14:55).
    assert sub9_inicio in (SABADO.replace(hour=13, minute=5), SABADO.replace(hour=14, minute=55))


def test_t7_3_ubicar_un_partido_mas_pesa_mas_que_cualquier_espera() -> None:
    sub9 = todos_contra_todos(list("AB"), "Sub 9", ("C1",))
    sub11 = todos_contra_todos(list("CD"), "Sub 11", ("C1",))
    pares = (ParDeEquipos("Sub 9:A", "Sub 11:C", "profe"),)
    manana = SABADO.replace(hour=8), SABADO.replace(hour=9)
    tarde = SABADO.replace(hour=15), SABADO.replace(hour=16)
    resultado = programar(con(problema(sub9 + sub11, [manana, tarde]), pares=pares), segundos=10)
    assert resultado.sin_ubicar == []  # 6 horas de espera, pero los dos juegan


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


def test_t11_4_la_eliminacion_puede_ir_antes_de_su_fin_de_semana_sugerido() -> None:
    # P33: "a veces semis o finales van antes". El fin de semana sugerido ya no es un límite:
    # sin lugar después, las llaves van apenas terminan los grupos.
    partidos = grupo_y_llaves()
    # Tres días: con dos, un equipo jugaría grupos, semi y final el mismo día (A1, P47).
    franjas = [franja(d, 8, 16) for d in (0, 1, 2)]
    desde = SABADO + timedelta(days=7)  # un fin de semana sin franjas
    prob = con(problema(partidos, franjas), eliminacion_desde=desde)
    resultado = programar(prob, segundos=15)
    assert resultado.sin_ubicar == []
    assert choques(prob, resultado) == []


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


def test_t10_2_con_ultimo_inicio_el_partido_puede_empezar_a_la_hora_final() -> None:
    # Respuesta a 1.1: "la hora final significa el inicio del último partido".
    # Dos partidos sin equipos en común, en una sola cancha.
    partidos = todos_contra_todos(list("AB"), "Sub 9", ("C1",)) + todos_contra_todos(
        list("CD"), "Sub 9", ("C1",)
    )
    franjas = [franja(0, 8, 9)]
    hasta_el_final = programar(problema(partidos, franjas), segundos=5)
    assert len(hasta_el_final.ubicados) == 1  # 8:00; el siguiente no termina antes de las 9
    ultimo_inicio = con(problema(partidos, franjas), reglas=Reglas(fin_de_franja="ultimo_inicio"))
    resultado = programar(ultimo_inicio, segundos=5)
    assert len(resultado.ubicados) == 2  # 8:00 y 8:50
    assert max(i for _, i in resultado.ubicados.values()) <= SABADO.replace(hour=9)
    assert choques(ultimo_inicio, resultado) == []


def test_t10_3_una_categoria_que_no_juega_los_viernes() -> None:
    # P56: Sub 5 y Sub 6 no juegan los viernes.
    partidos = [
        PartidoAProgramar(**{**p.__dict__, "dias_sin_jugar": frozenset({4})})
        for p in todos_contra_todos(list("AB"))
    ]
    viernes = SABADO - timedelta(days=1)
    franjas = [(viernes.replace(hour=16), viernes.replace(hour=20)), franja(0, 8, 16)]
    resultado = programar(problema(partidos, franjas), segundos=5)
    assert all(i.weekday() == 5 for _, i in resultado.ubicados.values())


def test_t10_3_los_chicos_van_en_los_primeros_horarios() -> None:
    chicos = [
        PartidoAProgramar(**{**p.__dict__, "temprano": True})
        for p in todos_contra_todos(list("AB"), "Sub 5", ("C1",))
    ]
    grandes = todos_contra_todos(list("CD"), "Sub 9", ("C1",))
    resultado = programar(problema(chicos + grandes, [franja(0, 8, 16)]), segundos=5)
    assert resultado.ubicados[chicos[0].id][1] == SABADO.replace(hour=8)


def test_t10_6_con_lugar_un_equipo_no_juega_dos_veces_el_mismo_dia() -> None:
    # P17/P47: se permite, pero "de preferencia evitar que un equipo juegue 2 partidos en un día".
    partidos = [
        PartidoAProgramar(**{**p.__dict__, "fecha": i + 1})
        for i, p in enumerate(todos_contra_todos(list("ABC")))
    ]
    resultado = programar(
        problema(partidos, [franja(0, 8, 16), franja(1, 8, 16), franja(2, 8, 16)]), segundos=10
    )
    for equipo in "ABC":
        dias = [
            resultado.ubicados[p.id][1].date() for p in partidos if f"Sub 9:{equipo}" in p.equipos
        ]
        assert len(dias) == len(set(dias)), equipo


def test_t10_6_las_finales_de_preferencia_en_los_dos_ultimos_dias() -> None:
    final = PartidoAProgramar(
        id="final", categoria="Sub 9", equipos=("A", "B"), minutos_partido=45, minutos_turno=50,
        canchas=frozenset({"C1"}), fase="eliminacion", clave="oro_final",
    )  # fmt: skip
    viernes = SABADO - timedelta(days=1)
    franjas = [
        (viernes.replace(hour=16), viernes.replace(hour=20)),
        franja(0, 8, 16),
        franja(1, 8, 16),
    ]
    resultado = programar(problema([final], franjas), segundos=5)
    assert resultado.ubicados["final"][1].date() != viernes.date()


def test_t10_3_si_solo_hay_viernes_el_partido_no_se_ubica() -> None:
    partidos = [
        PartidoAProgramar(**{**p.__dict__, "dias_sin_jugar": frozenset({4})})
        for p in todos_contra_todos(list("AB"))
    ]
    viernes = SABADO - timedelta(days=1)
    resultado = programar(
        problema(partidos, [(viernes.replace(hour=16), viernes.replace(hour=20))]), segundos=5
    )
    assert resultado.sin_ubicar == [partidos[0].id]


# ---------- T11.2: partidos puestos a mano con avisos ----------


def fijar(partido: PartidoAProgramar, cancha: str, momento: datetime) -> PartidoAProgramar:
    return PartidoAProgramar(**{**partido.__dict__, "fijo": (cancha, momento)})


def test_t11_2_un_partido_fijo_fuera_de_horario_no_rompe_el_modelo() -> None:
    partidos = todos_contra_todos(list("ABCD"))
    jueves = SABADO - timedelta(days=2)  # un día sin franjas
    tarde = SABADO.replace(hour=17)  # después de la franja del sábado
    partidos[0] = fijar(partidos[0], "C2", jueves.replace(hour=18))
    partidos[1] = fijar(partidos[1], "C1", tarde)
    prob = problema(partidos, [franja(0, 8, 14), franja(1, 8, 14)])
    resultado = programar(prob, segundos=10)
    assert resultado.ubicados[partidos[0].id] == ("C2", jueves.replace(hour=18))
    assert resultado.ubicados[partidos[1].id] == ("C1", tarde)
    assert resultado.sin_ubicar == []


def test_t11_2_dos_fijos_que_rompen_una_regla_blanda_no_rompen_el_modelo() -> None:
    # A juega dos partidos seguidos, sin turno libre, y un profe compartido a la vez:
    # avisos que la organización confirmó. El resto se programa igual.
    partidos = todos_contra_todos(list("ABCD"))
    partidos[0] = fijar(partidos[0], "C1", SABADO.replace(hour=8))  # A-B
    partidos[1] = fijar(partidos[1], "C2", SABADO.replace(hour=8, minute=50))  # A-C
    otros = todos_contra_todos(list("EF"))
    otros[0] = fijar(otros[0], "C2", SABADO.replace(hour=8))
    prob = Problema(
        partidos=tuple(partidos + otros),
        fisicas=FISICAS,
        franjas=(franja(0, 8, 14), franja(1, 8, 14)),
        reglas=Reglas(),
        pares=(ParDeEquipos("Sub 9:B", "Sub 9:E", "profe"),),
    )
    resultado = programar(prob, segundos=10)
    assert resultado.sin_ubicar == []


def test_t11_4_p20_los_equipos_de_un_club_juegan_el_mismo_dia() -> None:
    # Tres clubes con un equipo en Sub 9 y otro en Sub 7. Hay lugar para 2 partidos por día
    # y 3 días: la única forma de que cada club juegue un solo día es juntar sus 2 partidos.
    def p(id: str, a: str, b: str) -> PartidoAProgramar:
        return PartidoAProgramar(
            id=id,
            categoria=id[0],
            equipos=(a, b),
            minutos_partido=45,
            minutos_turno=50,
            canchas=frozenset({"C2"}),
        )

    partidos = [p("x01", "x0", "x1"), p("x23", "x2", "x3"), p("x45", "x4", "x5")]
    partidos += [p("y01", "y0", "y1"), p("y23", "y2", "y3"), p("y45", "y4", "y5")]
    clubes = {f"{c}{i}": f"club {i // 2}" for c in "xy" for i in range(6)}
    franjas = [franja(d, 8, 10) for d in (0, 1, 7)]  # 8:00 y 8:50: dos partidos por día
    prob = con(problema(partidos, franjas), clubes=clubes)
    resultado = programar(prob, segundos=15)
    assert resultado.sin_ubicar == []
    for club in set(clubes.values()):
        dias = {
            resultado.ubicados[q.id][1].date()
            for q in partidos
            if any(clubes[str(e)] == club for e in q.equipos_definidos)
        }
        assert len(dias) == 1, club


# ---------- A1 (fase 12): máximo por día entre grupos y eliminación ----------


def test_a1_un_equipo_de_grupos_no_puede_jugar_semi_y_final_el_mismo_dia() -> None:
    # Un solo día: la fecha 3 de grupos, las semis y la final no pueden ir todos ahí.
    partidos = grupo_y_llaves()
    partidos = [
        PartidoAProgramar(**{**p.__dict__, "ronda": "final" if "final" in p.clave else "semi"})
        if p.fase == "eliminacion"
        else p
        for p in partidos
    ]
    franjas = [franja(0, 8, 20), franja(1, 8, 20)]
    prob = problema(partidos, franjas)
    resultado = programar(prob, segundos=15)
    por_dia: dict[object, list[str]] = {}
    for id_, (_, inicio) in resultado.ubicados.items():
        por_dia.setdefault(inicio.date(), []).append(str(id_))
    for ids in por_dia.values():
        grupos = [i for i in ids if i.startswith("g")]
        rondas = {"semi" for i in ids if i.startswith("s")} | {"final" for i in ids if i == "f"}
        for equipo in "ABCD":
            suyos = [g for g in grupos for p in partidos if p.id == g and equipo in p.equipos]
            assert len(suyos) + len(rondas) <= 2, (equipo, ids)


# ---------- A2 (fase 12): orden de fechas "blanda" se penaliza ----------


def _al_reves(prob: Problema, resultado: Resultado) -> int:
    por_equipo: dict[object, list[PartidoAProgramar]] = {}
    for p in prob.partidos:
        if p.fecha and p.id in resultado.ubicados:
            for e in p.equipos_definidos:
                por_equipo.setdefault(e, []).append(p)
    reves = 0
    for suyos in por_equipo.values():
        suyos.sort(key=lambda p: p.fecha or 0)
        for antes, despues in pairwise(suyos):
            if resultado.ubicados[despues.id][1] < resultado.ubicados[antes.id][1]:
                reves += 1
    return reves


def test_a2_con_orden_blanda_y_lugar_ninguna_fecha_queda_al_reves() -> None:
    from pathlib import Path

    from dominio.fixture import armar_fixture
    from dominio.formatos import cargar_formatos

    formatos = cargar_formatos(Path(__file__).resolve().parents[2] / "datos/config/formatos.json")
    fixture = armar_fixture(
        formatos.para(6),
        list("ABCDEF"),
        lambda e: e,
        semilla=1,
        separar_clubes=False,
        mismo_club_fecha_1=False,
    )
    partidos = [
        PartidoAProgramar(
            id=f"g{i}",
            categoria="Sub 9",
            equipos=(p.local, p.visitante),
            minutos_partido=45,
            minutos_turno=50,
            canchas=frozenset({"C1", "C2"}),
            fecha=p.fecha,
        )
        for i, p in enumerate(fixture.partidos)
        if p.fase == "grupos"
    ]
    # Un solo fin de semana: el reparto entre semanas no ayuda a ordenar.
    prob = Problema(
        partidos=tuple(partidos),
        fisicas=FISICAS,
        franjas=(franja(0, 8, 18), franja(1, 8, 18)),
        reglas=Reglas(orden_de_fechas="blanda"),
    )
    resultado = programar(prob, segundos=15, trabajadores=4)
    assert resultado.sin_ubicar == []
    assert _al_reves(prob, resultado) == 0


# ---------- A4 (fase 12): tiempo extra solo para lo que no entra ----------


def test_a4_con_lugar_en_el_horario_normal_no_se_usa_el_extra() -> None:
    from dominio.verificador import FranjaExtra

    jueves = FranjaExtra(
        SABADO.replace(hour=16) - timedelta(days=2), SABADO.replace(hour=20) - timedelta(days=2)
    )
    prob = con(
        problema(todos_contra_todos(list("ABCD")), [franja(0, 8, 14), franja(1, 8, 14)]),
        extras=(jueves,),
    )
    resultado = programar(prob, segundos=10)
    assert resultado.sin_ubicar == []
    assert all(inicio.weekday() != 3 for _, inicio in resultado.ubicados.values())


def test_a4_lo_que_no_entra_va_al_extra_y_solo_en_sus_canchas() -> None:
    from dominio.verificador import FranjaExtra

    # Una sola hora el sábado en C1 y C2: entran 2 partidos de 6. El jueves, solo en C2.
    jueves = FranjaExtra(
        SABADO.replace(hour=16) - timedelta(days=2),
        SABADO.replace(hour=22) - timedelta(days=2),
        frozenset({"C2"}),
    )
    prob = con(problema(todos_contra_todos(list("ABCD")), [franja(0, 8, 9)]), extras=(jueves,))
    resultado = programar(prob, segundos=10)
    assert resultado.sin_ubicar == []
    en_jueves = [(c, i) for c, i in resultado.ubicados.values() if i.weekday() == 3]
    assert len(en_jueves) == 4
    assert {c for c, _ in en_jueves} == {"C2"}
    assert choques(prob, resultado) == []


def test_a2_si_exigir_el_orden_deja_algo_afuera_se_permite_al_revés() -> None:
    # La fecha 2 está puesta a las 08:00; la fecha 1 solo entra en la franja de la tarde.
    a1 = PartidoAProgramar(
        id="f1",
        categoria="Sub 9",
        equipos=("A", "B"),
        minutos_partido=45,
        minutos_turno=50,
        canchas=frozenset({"C2"}),
        fecha=1,
    )
    a2 = PartidoAProgramar(
        id="f2",
        categoria="Sub 9",
        equipos=("A", "C"),
        minutos_partido=45,
        minutos_turno=50,
        canchas=frozenset({"C2"}),
        fecha=2,
        fijo=("C2", SABADO.replace(hour=8)),
    )
    prob = Problema(
        partidos=(a1, a2),
        fisicas=FISICAS,
        franjas=(franja(0, 8, 8), franja(0, 14, 15)),
        reglas=Reglas(orden_de_fechas="blanda"),
    )
    resultado = programar(prob, segundos=10)
    assert resultado.sin_ubicar == []
    assert resultado.ubicados["f1"][1] > resultado.ubicados["f2"][1]  # al revés, pero entra
