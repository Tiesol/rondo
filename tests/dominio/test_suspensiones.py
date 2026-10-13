"""T8.9: suspensiones (B5, P29, P74). Funciones puras: partidos y tarjetas de un jugador."""

from dominio.suspensiones import Incidente, Suspension, incidentes_de_tarjetas, suspendidos

# Los partidos del equipo, en orden: p1, p2, p3, p4.
ORDEN = {"E": ["p1", "p2", "p3", "p4"]}


def test_un_incidente_suspende_el_proximo_partido_de_su_equipo() -> None:
    incidentes = [Incidente("juan", "E", "p1", partidos=1, motivo="Doble amarilla")]
    assert suspendidos(incidentes, ORDEN) == [Suspension("juan", "p2", "Doble amarilla")]


def test_dos_partidos_suspenden_los_dos_siguientes() -> None:
    incidentes = [Incidente("juan", "E", "p2", partidos=2, motivo="Roja directa")]
    assert [s.partido for s in suspendidos(incidentes, ORDEN)] == ["p3", "p4"]


def test_si_no_quedan_partidos_no_hay_suspension_que_cumplir() -> None:
    assert suspendidos([Incidente("juan", "E", "p4", partidos=1, motivo="x")], ORDEN) == []


def test_doble_amarilla_sin_pagar_desde_sub_10() -> None:
    tarjetas = [("juan", "p1", "amarilla"), ("juan", "p1", "amarilla")]
    incidentes = incidentes_de_tarjetas(tarjetas, equipo_de={"juan": "E"}, edad=12, orden=ORDEN)
    assert [(i.jugador, i.partido, i.motivo) for i in incidentes] == [
        ("juan", "p1", "Doble amarilla sin pagar la multa")
    ]


def test_doble_amarilla_pagada_no_suspende() -> None:
    tarjetas = [("juan", "p1", "amarilla"), ("juan", "p1", "amarilla")]
    incidentes = incidentes_de_tarjetas(
        tarjetas, equipo_de={"juan": "E"}, edad=12, orden=ORDEN, pagadas={("juan", "p1")}
    )
    assert incidentes == []


def test_doble_amarilla_en_sub_8_no_suspende() -> None:
    # Sub 5 a Sub 9: dos amarillas sacan al jugador 5 minutos, nada más.
    tarjetas = [("juan", "p1", "amarilla"), ("juan", "p1", "amarilla")]
    assert incidentes_de_tarjetas(tarjetas, equipo_de={"juan": "E"}, edad=8, orden=ORDEN) == []


def test_roja_directa_por_defecto_no_suspende_sola() -> None:
    # P29: la decide la organización en cada caso.
    tarjetas = [("juan", "p1", "roja")]
    assert incidentes_de_tarjetas(tarjetas, equipo_de={"juan": "E"}, edad=12, orden=ORDEN) == []
    con_regla = incidentes_de_tarjetas(
        tarjetas, equipo_de={"juan": "E"}, edad=12, orden=ORDEN, partidos_por_roja=2
    )
    assert [(i.partido, i.partidos) for i in con_regla] == [("p1", 2)]


def test_la_roja_de_la_doble_amarilla_no_cuenta_como_directa() -> None:
    tarjetas = [("juan", "p1", "amarilla"), ("juan", "p1", "amarilla"), ("juan", "p1", "roja")]
    incidentes = incidentes_de_tarjetas(
        tarjetas, equipo_de={"juan": "E"}, edad=12, orden=ORDEN, partidos_por_roja=3
    )
    assert [i.motivo for i in incidentes] == ["Doble amarilla sin pagar la multa"]


def test_amarillas_acumuladas_si_la_regla_lo_dice() -> None:
    tarjetas = [("juan", "p1", "amarilla"), ("juan", "p2", "amarilla"), ("juan", "p3", "amarilla")]
    assert incidentes_de_tarjetas(tarjetas, equipo_de={"juan": "E"}, edad=12, orden=ORDEN) == []
    acumuladas = incidentes_de_tarjetas(
        tarjetas, equipo_de={"juan": "E"}, edad=12, orden=ORDEN, amarillas_acumuladas=3
    )
    assert [(i.partido, i.motivo) for i in acumuladas] == [("p3", "3 amarillas acumuladas")]
