"""El resultado de un partido, a partir de lo que carga la mesa (T8.5, B3).

El marcador no se escribe: sale de los goles. Un gol en contra (P72) se anota a nombre del
equipo que lo hizo, sin jugador, y suma para el rival. Un W.O. da el marcador de la regla
(P23) al que se presentó. En la eliminación, un empate se define por penales.
"""

from dataclasses import dataclass
from typing import Literal

TipoDeEvento = Literal["gol", "gol_en_contra", "amarilla", "roja", "amonestacion"]
Lado = Literal["local", "visitante"]


class ResultadoInvalido(ValueError):
    """El partido no se puede terminar así; el mensaje dice por qué."""


@dataclass(frozen=True)
class Evento:
    tipo: TipoDeEvento
    lado: Lado  # el equipo del jugador (en un gol en contra, el que lo hizo)


def _otro(lado: Lado) -> Lado:
    return "visitante" if lado == "local" else "local"


@dataclass(frozen=True)
class Resultado:
    marcador: tuple[int, int]
    penales: tuple[int, int] | None
    eliminacion: bool
    wo: bool

    @property
    def ganador(self) -> Lado | None:
        local, visitante = self.marcador
        if local != visitante:
            return "local" if local > visitante else "visitante"
        if self.penales and self.penales[0] != self.penales[1]:
            return "local" if self.penales[0] > self.penales[1] else "visitante"
        return None

    def revisar_para_terminar(self) -> None:
        if self.eliminacion and self.ganador is None:
            raise ResultadoInvalido(
                "En la eliminación no hay empate: faltan los penales, y tienen que definir."
            )


def resultado(
    eventos: list[Evento],
    *,
    no_se_presento: Lado | None = None,
    marcador_wo: tuple[int, int] = (3, 0),
    penales: tuple[int, int] | None = None,
    eliminacion: bool = False,
) -> Resultado:
    if no_se_presento is not None:
        a_favor, en_contra = marcador_wo
        marcador = (en_contra, a_favor) if no_se_presento == "local" else (a_favor, en_contra)
        return Resultado(marcador, None, eliminacion, wo=True)
    goles = {"local": 0, "visitante": 0}
    for evento in eventos:
        if evento.tipo == "gol":
            goles[evento.lado] += 1
        elif evento.tipo == "gol_en_contra":
            goles[_otro(evento.lado)] += 1
    marcador = (goles["local"], goles["visitante"])
    return Resultado(marcador, penales, eliminacion, wo=False)
