"""T7.1: la eliminación respeta el turno libre del equipo (P17), en el modelo y en el verificador.

Revisión externa de la fase 4, punto 1: las llaves tienen participantes "por definir", así que
no se les aplicaban las restricciones de equipo. Ahora cada resultado de una llave (ganador o
perdedor) es un equipo virtual, y una llave que toma posiciones de grupo descansa después del
último partido de grupos del día.
"""

from datetime import datetime, timedelta
from itertools import combinations
from pathlib import Path

from dominio.config import Reglas
from dominio.formatos import cargar_formatos, equipos_virtuales, toman_posiciones
from dominio.programador.modelo import PartidoAProgramar, Problema, programar
from dominio.verificador import Escenario, PartidoAgendado, verificar

FISICAS = {"C1": frozenset({"C1"}), "C2": frozenset({"C2"}), "C3": frozenset({"C3"})}
SABADO = datetime(2026, 11, 14)
FORMATOS = cargar_formatos(
    Path(__file__).resolve().parents[2] / "datos" / "config" / "formatos.json"
)


def _p(id: str, equipos: tuple[str | None, str | None], **extra: object) -> PartidoAProgramar:
    return PartidoAProgramar(
        id=id,
        categoria="Sub 9",
        equipos=equipos,
        minutos_partido=45,
        minutos_turno=50,
        canchas=frozenset({"C1", "C2"}),
        **extra,  # type: ignore[arg-type]
    )


def cuatro_equipos() -> list[PartidoAProgramar]:
    """Formato de 4: todos contra todos, semis 1.º-4.º y 2.º-3.º, final y final de Plata."""
    formato = FORMATOS.para(4)
    virtuales = equipos_virtuales(formato)
    posiciones = toman_posiciones(formato)
    grupos = [
        _p(f"g{i}", (a, b), fecha=1 + i // 2) for i, (a, b) in enumerate(combinations("ABCD", 2))
    ]
    llaves = [
        _p(
            llave.clave,
            (None, None),
            fase="eliminacion",
            clave=llave.clave,
            despues_de=frozenset(
                llave.local.participante.partidos_referidos
                + llave.visitante.participante.partidos_referidos
            ),
            virtuales=virtuales[llave.clave],
            toma_posiciones=llave.clave in posiciones,
        )
        for llave in formato.eliminacion
    ]
    return grupos + llaves


def test_equipos_virtuales_del_formato_de_4() -> None:
    virtuales = equipos_virtuales(FORMATOS.para(4))
    # Cada semi "contiene" a su ganador y a su perdedor; la final, a los ganadores.
    assert virtuales["oro_semi_1"] >= {
        "ganador de la semi 1 de Oro",
        "perdedor de la semi 1 de Oro",
    }
    assert virtuales["oro_final"] == {"ganador de la semi 1 de Oro", "ganador de la semi 2 de Oro"}
    assert virtuales["plata_final"] == {
        "perdedor de la semi 1 de Oro",
        "perdedor de la semi 2 de Oro",
    }
    assert toman_posiciones(FORMATOS.para(4)) == {"oro_semi_1", "oro_semi_2"}


def test_mejor_perdedor_es_cualquiera_de_los_perdedores() -> None:
    virtuales = equipos_virtuales(FORMATOS.para(6))
    plata_final = virtuales["plata_final"]
    assert {"perdedor de la semi 1 de Oro", "perdedor de la semi 2 de Oro"} <= plata_final


def test_con_una_sola_franja_la_final_queda_a_semi_mas_dos_turnos() -> None:
    partidos = cuatro_equipos()
    franja = (SABADO.replace(hour=8), SABADO.replace(hour=20))
    # Todo en un día: cada equipo juega 3 partidos de grupos, así que se sube el máximo (P47).
    reglas = Reglas(max_partidos_por_dia=5)
    prob = Problema(partidos=tuple(partidos), fisicas=FISICAS, franjas=(franja,), reglas=reglas)
    resultado = programar(prob, segundos=20)
    assert resultado.sin_ubicar == []
    inicio = {i: resultado.ubicados[i][1] for i in resultado.ubicados}
    dos_turnos = timedelta(minutes=2 * 50)
    for final in ("oro_final", "plata_final"):
        assert inicio[final] >= max(inicio["oro_semi_1"], inicio["oro_semi_2"]) + dos_turnos
    ultimo_de_grupos = max(inicio[f"g{i}"] for i in range(6))
    assert min(inicio["oro_semi_1"], inicio["oro_semi_2"]) >= ultimo_de_grupos + dos_turnos


# ---------- Verificador ----------


def agendado(
    id: str,
    cancha: str,
    hora: str,
    *,
    turno: int = 70,
    equipos: tuple[str | None, str | None] = (None, None),
    **extra: object,
) -> PartidoAgendado:
    h, m = (int(x) for x in hora.split(":"))
    return PartidoAgendado(
        id=id,
        categoria="Sub 15|avanzado",
        equipos=equipos,
        cancha=cancha,
        inicio=SABADO.replace(hour=h, minute=m),
        minutos_partido=turno - 5,
        minutos_turno=turno,
        **extra,  # type: ignore[arg-type]
    )


def escenario() -> Escenario:
    return Escenario(
        fisicas=FISICAS,
        compatibilidad={"Sub 15|avanzado": frozenset({"C3"})},
        franjas=((SABADO.replace(hour=8), SABADO.replace(hour=20)),),
        pares=(),
        bloqueos=(),
        reglas=Reglas(),
    )


def test_el_verificador_marca_el_caso_de_sub_15_de_la_revision() -> None:
    # Semi 1 de Oro a las 17:10 y la final a las 18:20, las dos en C3 (F11, turno de 70).
    ganador = "ganador de la semi 1 de Oro"
    semi = agendado("semi", "C3", "17:10", fase="eliminacion", virtuales=frozenset({ganador}))
    final = agendado("final", "C3", "18:20", fase="eliminacion", virtuales=frozenset({ganador}))
    choques = verificar([semi, final], escenario())
    assert [(c.tipo, c.partidos) for c in choques] == [("equipo", ("semi", "final"))]
    assert ganador in choques[0].motivos[0]


def test_con_dos_turnos_de_distancia_no_hay_choque() -> None:
    ganador = frozenset({"ganador de la semi 1 de Oro"})
    semi = agendado("semi", "C3", "08:00", fase="eliminacion", virtuales=ganador)
    final = agendado("final", "C3", "10:20", fase="eliminacion", virtuales=ganador)
    assert verificar([semi, final], escenario()) == []


def test_la_semi_descansa_despues_del_ultimo_partido_de_grupos_del_dia() -> None:
    grupo = agendado("g", "C3", "08:00", equipos=("A", "B"))
    semi = agendado("semi", "C3", "09:10", fase="eliminacion", toma_posiciones=True)
    choques = verificar([grupo, semi], escenario())
    assert [(c.tipo, c.partidos) for c in choques] == [("equipo", ("g", "semi"))]
    lejos = agendado("semi", "C3", "10:30", fase="eliminacion", toma_posiciones=True)
    assert verificar([grupo, lejos], escenario()) == []
