"""B6 (fase 12): reglas aflojadas solo para una reprogramación."""

from dataclasses import replace
from datetime import datetime, timedelta

from dominio.config import Reglas
from dominio.programador.modelo import PartidoAProgramar, Problema
from dominio.programador.relajar import Relajar, aplicar

SAB = datetime(2026, 10, 24)
FISICAS = {
    "C1": frozenset({"C1A", "C1B"}),
    "C1A": frozenset({"C1A"}),
    "C1B": frozenset({"C1B"}),
    "C3": frozenset({"C3"}),
}


def problema() -> Problema:
    partido = PartidoAProgramar(
        id=1,
        categoria="Sub 9",
        equipos=("A", "B"),
        minutos_partido=45,
        minutos_turno=50,
        canchas=frozenset({"C1"}),
    )
    grande = replace(partido, id=2, categoria="Sub 12", canchas=frozenset({"C3"}))
    franja = (SAB.replace(hour=8), SAB.replace(hour=16))
    return Problema(partidos=(partido, grande), fisicas=FISICAS, franjas=(franja,), reglas=Reglas())


def test_sin_aflojar_nada_es_el_mismo_problema() -> None:
    assert aplicar(problema(), Relajar()) is not None
    assert aplicar(problema(), Relajar()) == problema()


def test_las_reglas_cambian_solo_en_la_copia() -> None:
    original = problema()
    flojo = aplicar(original, Relajar(turnos_libres=0, max_por_dia=3, orden="blanda"))
    assert (flojo.reglas.turnos_libres_mismo_dia, flojo.reglas.max_partidos_por_dia) == (0, 3)
    assert flojo.reglas.orden_de_fechas == "blanda"
    assert original.reglas.turnos_libres_mismo_dia == Reglas().turnos_libres_mismo_dia


def test_empezar_antes_o_terminar_despues_agrega_tiempo_extra_en_la_ventana() -> None:
    flojo = aplicar(problema(), Relajar(minutos_extra=30))
    (extra,) = flojo.extras
    assert extra.desde == SAB.replace(hour=8) - timedelta(minutes=30)
    assert extra.hasta == SAB.replace(hour=16) + timedelta(minutes=30)
    fuera = aplicar(
        problema(),
        Relajar(minutos_extra=30),
        ventana=(SAB + timedelta(days=5), SAB + timedelta(days=9)),
    )
    assert fuera.extras == ()


def test_usar_mitades_no_vale_para_las_categorias_que_no_caben() -> None:
    flojo = aplicar(problema(), Relajar(usar_mitades=True), sin_mitades={"Sub 12"})
    chico, grande = flojo.partidos
    assert chico.canchas == frozenset({"C1", "C1A", "C1B"})
    assert grande.canchas == frozenset({"C3"})


def test_se_guarda_y_se_describe() -> None:
    r = Relajar(turnos_libres=0, minutos_extra=20, usar_mitades=True)
    assert Relajar.desde_dict(r.a_dict()) == r
    assert len(r.describir()) == 3
