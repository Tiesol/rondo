"""PRO-13: propuestas de reprogramación ante un bloqueo nuevo."""

from dataclasses import replace
from datetime import datetime, timedelta
from itertools import combinations

from dominio.config import Reglas
from dominio.programador.modelo import PartidoAProgramar, Problema, programar
from dominio.programador.reprogramar import proponer
from dominio.verificador import Bloqueo, Escenario, PartidoAgendado, verificar

FISICAS = {"C1": frozenset({"C1"}), "C2": frozenset({"C2"})}
SAB = datetime(2026, 10, 24)


def franjas() -> tuple[tuple[datetime, datetime], ...]:
    return tuple(
        (SAB + timedelta(days=d, hours=8), SAB + timedelta(days=d, hours=13)) for d in (0, 1, 7, 8)
    )


def partidos(equipos: str = "ABCDEF") -> list[PartidoAProgramar]:
    return [
        PartidoAProgramar(
            id=f"{a}-{b}",
            categoria="Sub 9",
            equipos=(a, b),
            minutos_partido=45,
            minutos_turno=50,
            canchas=frozenset({"C1", "C2"}),
        )
        for a, b in combinations(equipos, 2)
    ]


def base() -> tuple[Problema, dict[object, tuple[str, datetime]]]:
    problema = Problema(
        partidos=tuple(partidos()), fisicas=FISICAS, franjas=franjas(), reglas=Reglas()
    )
    # Con un solo trabajador, el solver es determinista: el test no depende de la suerte.
    resultado = programar(problema, segundos=10, trabajadores=1)
    assert resultado.sin_ubicar == []
    return problema, dict(resultado.ubicados)


def sin_choques(problema: Problema, calendario: dict[object, tuple[str, datetime]]) -> bool:
    agendados = [
        PartidoAgendado(
            id=p.id,
            categoria=p.categoria,
            equipos=p.equipos,
            cancha=calendario[p.id][0],
            inicio=calendario[p.id][1],
            minutos_partido=p.minutos_partido,
            minutos_turno=p.minutos_turno,
        )
        for p in problema.partidos
        if p.id in calendario
    ]
    escenario = Escenario(
        fisicas=problema.fisicas,
        compatibilidad={"Sub 9": frozenset({"C1", "C2"})},
        franjas=problema.franjas,
        pares=problema.pares,
        bloqueos=problema.bloqueos,
        reglas=problema.reglas,
    )
    return verificar(agendados, escenario) == []


def con_bloqueo_sobre_uno() -> tuple[Problema, dict[object, tuple[str, datetime]], object]:
    problema, actual = base()
    victima = min(problema.partidos, key=lambda p: actual[p.id][1])
    _, inicio = actual[victima.id]
    bloqueo = Bloqueo(
        victima.equipos[0], inicio - timedelta(minutes=10), inicio + timedelta(hours=1)
    )
    return replace(problema, bloqueos=(bloqueo,)), actual, victima.id


def test_pro_13_da_dos_o_tres_propuestas_validas_y_ordenadas() -> None:
    problema, actual, victima = con_bloqueo_sobre_uno()
    propuestas = proponer(problema, actual, desde=SAB, hasta=SAB + timedelta(days=9), segundos=10)
    assert 2 <= len(propuestas) <= 3
    cantidades = [len(p.movimientos) for p in propuestas]
    assert cantidades == sorted(cantidades)
    for propuesta in propuestas:
        assert victima in {m.partido for m in propuesta.movimientos}
        assert sin_choques(problema, propuesta.calendario(actual))


def test_pro_13_las_propuestas_son_distintas() -> None:
    problema, actual, _ = con_bloqueo_sobre_uno()
    propuestas = proponer(problema, actual, desde=SAB, hasta=SAB + timedelta(days=9), segundos=10)
    conjuntos = [frozenset(m.partido for m in p.movimientos) for p in propuestas]
    assert len(set(conjuntos)) == len(conjuntos)


def test_pro_13_no_mueve_lo_que_queda_fuera_de_la_ventana_ni_lo_fijo() -> None:
    problema, actual, victima = con_bloqueo_sobre_uno()
    por_hora = sorted(problema.partidos, key=lambda p: actual[p.id][1])
    jugado = next(p for p in por_hora if p.id != victima)
    hasta = actual[jugado.id][1] + timedelta(days=1)
    partidos_ = tuple(
        replace(p, fijo=actual[p.id]) if p.id == jugado.id else p for p in problema.partidos
    )
    problema = replace(problema, partidos=partidos_)
    propuestas = proponer(problema, actual, desde=SAB, hasta=hasta, segundos=10)
    assert propuestas
    for propuesta in propuestas:
        for movimiento in propuesta.movimientos:
            assert movimiento.partido != jugado.id
            assert movimiento.antes is not None and movimiento.despues is not None
            assert SAB <= movimiento.antes[1] < hasta
            assert SAB <= movimiento.despues[1] < hasta


def test_sin_choque_no_hay_nada_que_mover() -> None:
    problema, actual = base()
    propuestas = proponer(problema, actual, desde=SAB, hasta=SAB + timedelta(days=9), segundos=5)
    assert propuestas == []


def test_si_no_hay_forma_no_inventa() -> None:
    problema, actual, _ = con_bloqueo_sobre_uno()
    # Una ventana de un solo partido de largo: no hay a dónde mover.
    victima_inicio = min(i for _, i in actual.values())
    propuestas = proponer(
        problema,
        actual,
        desde=victima_inicio,
        hasta=victima_inicio + timedelta(minutes=1),
        segundos=5,
    )
    assert all(sin_choques(problema, p.calendario(actual)) for p in propuestas)


def test_pro_13_no_mueve_nada_antes_de_la_ventana() -> None:
    """Revisión de la fase 5: el límite inferior de la ventana también se respeta.

    Un solo partido, en el segundo fin de semana, con un bloqueo que ocupa todo ese fin de
    semana. El primero está libre, pero queda fuera de la ventana: no hay propuesta posible.
    """
    segunda = SAB + timedelta(days=7)
    solo = partidos("AB")[0]
    problema = Problema(
        partidos=(solo,),
        fisicas=FISICAS,
        franjas=franjas(),
        reglas=Reglas(),
        bloqueos=(Bloqueo("A", segunda, segunda + timedelta(days=2)),),
    )
    actual = {solo.id: ("C1", segunda + timedelta(hours=9))}
    propuestas = proponer(
        problema, actual, desde=segunda, hasta=segunda + timedelta(days=7), segundos=5
    )
    assert propuestas == []
