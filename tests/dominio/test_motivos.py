"""PRO-14: cada partido sin ubicar dice por qué."""

from datetime import datetime

from dominio.config import Reglas
from dominio.programador.modelo import PartidoAProgramar, Problema, Resultado
from dominio.programador.motivos import motivos_sin_ubicar
from dominio.verificador import Bloqueo, ParDeEquipos

SAB = datetime(2026, 10, 24)
FISICAS = {"C1": frozenset({"C1"}), "C2": frozenset({"C2"}), "C3": frozenset({"C3"})}


def p(
    id: str, equipos: tuple[str, str], canchas: set[str], turno: int = 50, **extra: object
) -> PartidoAProgramar:
    return PartidoAProgramar(
        id=id,
        categoria="Sub 9",
        equipos=equipos,
        minutos_partido=turno - 5,
        minutos_turno=turno,
        canchas=frozenset(canchas),
        **extra,  # type: ignore[arg-type]
    )


def problema(
    partidos: list[PartidoAProgramar], hasta: tuple[int, int], **extra: object
) -> Problema:
    return Problema(
        partidos=tuple(partidos),
        fisicas=FISICAS,
        franjas=((SAB.replace(hour=8), SAB.replace(hour=hasta[0], minute=hasta[1])),),
        reglas=Reglas(),
        **extra,  # type: ignore[arg-type]
    )


def test_sin_cancha_libre() -> None:
    ocupado = p("x", ("A", "B"), {"C3"})
    afuera = p("y", ("C", "D"), {"C3"})
    prob = problema([ocupado, afuera], (8, 50))
    resultado = Resultado(ubicados={"x": ("C3", SAB.replace(hour=8))}, sin_ubicar=["y"])
    assert motivos_sin_ubicar(prob, resultado)["y"].startswith("No queda ningún turno libre en C3")


def test_solo_choca_con_un_profe() -> None:
    a = p("a", ("A", "B"), {"C1"})
    c = p("c", ("C", "D"), {"C2"})
    prob = problema([a, c], (8, 50), pares=(ParDeEquipos("A", "C", "profe"),))
    resultado = Resultado(ubicados={"a": ("C1", SAB.replace(hour=8))}, sin_ubicar=["c"])
    assert "profe" in motivos_sin_ubicar(prob, resultado)["c"]


def test_choque_de_equipo() -> None:
    uno = p("uno", ("A", "B"), {"C1", "C2"})
    otro = p("otro", ("A", "C"), {"C1", "C2"})
    prob = problema([uno, otro], (9, 30))
    resultado = Resultado(ubicados={"uno": ("C1", SAB.replace(hour=8))}, sin_ubicar=["otro"])
    assert "equipo" in motivos_sin_ubicar(prob, resultado)["otro"].lower()


def test_bloqueo() -> None:
    solo = p("s", ("A", "B"), {"C1"})
    bloqueo = Bloqueo("A", SAB.replace(hour=7), SAB.replace(hour=12))
    prob = problema([solo], (9, 0), bloqueos=(bloqueo,))
    assert "bloqueo" in motivos_sin_ubicar(prob, Resultado(sin_ubicar=["s"]))["s"]


def test_no_entra_en_ninguna_franja() -> None:
    largo = p("l", ("A", "B"), {"C3"}, turno=70)
    prob = problema([largo], (9, 0))
    assert "ninguna franja" in motivos_sin_ubicar(prob, Resultado(sin_ubicar=["l"]))["l"]


def test_sin_canchas_compatibles() -> None:
    raro = p("r", ("A", "B"), set())
    prob = problema([raro], (12, 0))
    assert "canchas compatibles" in motivos_sin_ubicar(prob, Resultado(sin_ubicar=["r"]))["r"]


def test_la_eliminacion_espera_a_sus_partidos() -> None:
    semi = p("semi", ("A", "B"), {"C1"}, fase="eliminacion", clave="oro_semi")
    final = p(
        "final",
        ("C", "D"),
        {"C1"},
        fase="eliminacion",
        clave="oro_final",
        despues_de=frozenset({"oro_semi"}),
    )
    prob = problema([semi, final], (12, 0))
    motivo = motivos_sin_ubicar(prob, Resultado(sin_ubicar=["semi", "final"]))["final"]
    assert "Semi" in motivo or "oro_semi" in motivo


def test_si_hay_lugar_lo_dice() -> None:
    libre = p("l", ("A", "B"), {"C1"})
    prob = problema([libre], (12, 0))
    motivo = motivos_sin_ubicar(prob, Resultado(sin_ubicar=["l"]))["l"]
    assert "tiempo" in motivo


def test_cada_partido_sin_ubicar_tiene_motivo() -> None:
    partidos = [p(f"x{i}", (f"A{i}", f"B{i}"), {"C1"}) for i in range(6)]
    prob = problema(partidos, (9, 0))
    resultado = Resultado(
        ubicados={"x0": ("C1", SAB.replace(hour=8))}, sin_ubicar=[f"x{i}" for i in range(1, 6)]
    )
    motivos = motivos_sin_ubicar(prob, resultado)
    assert set(motivos) == {f"x{i}" for i in range(1, 6)}
    assert all(motivos.values())
