"""Validaciones de inscripción (SPEC, INS-02 a INS-11), sin base de datos.

Cada función recibe datos simples y la configuración, y devuelve hallazgos: un error impide
guardar; un aviso se muestra, pero se guarda igual. El servicio de inscripción arma la entrada
con lo que hay en la base y decide.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

from dominio.config import CuerpoTecnico, Reglas
from dominio.documentos import Documento

NivelHallazgo = Literal["error", "aviso"]
Rol = Literal["jugador", "profe"]

DORSAL_MINIMO, DORSAL_MAXIMO = 1, 99  # supuesto: los dorsales de una camiseta de fútbol


@dataclass(frozen=True)
class Hallazgo:
    nivel: NivelHallazgo
    regla: str
    mensaje: str


@dataclass(frozen=True)
class EquipoRef:
    """Lo que hace falta saber de un equipo para comparar: su club y su categoría."""

    id: int
    club: str
    categoria: str  # "Sub 9"
    categoria_nivel: str  # "Sub 9 Avanzado"

    @property
    def descripcion(self) -> str:
        return f"{self.categoria_nivel} de {self.club}"


@dataclass(frozen=True)
class Participacion:
    """Un equipo donde la persona ya está, y con qué rol."""

    equipo: EquipoRef
    rol: Rol


@dataclass(frozen=True)
class CategoriaDelEquipo:
    edad: int
    anios_nacimiento: int
    min_jugadores: int
    max_jugadores: int


@dataclass(frozen=True)
class AltaDeJugador:
    equipo: EquipoRef
    categoria: CategoriaDelEquipo
    anio_torneo: int
    nacimiento: date | None
    documento: Documento | None
    dorsal: int | None
    jugadores_en_el_equipo: int  # sin contar al que se agrega
    dorsales_en_el_equipo: frozenset[int]
    otras_participaciones: tuple[Participacion, ...]


@dataclass(frozen=True)
class AltaDeProfe:
    equipo: EquipoRef
    rol: str  # entrenador, asistente o delegado (los de la configuración)
    documento: Documento | None
    roles_en_el_equipo: tuple[str, ...]  # el cuerpo técnico actual, sin el que se agrega
    otras_participaciones: tuple[Participacion, ...]


def validar_alta_de_jugador(alta: AltaDeJugador, reglas: Reglas) -> list[Hallazgo]:
    return [
        *validar_edad(alta, reglas),
        *validar_cantidad(alta),
        *validar_otros_equipos(alta.equipo, "jugador", alta.otras_participaciones, reglas),
        *validar_dorsal(alta.dorsal, alta.dorsales_en_el_equipo, reglas),
        *validar_documento(alta.documento, reglas),
    ]


def validar_alta_de_profe(
    alta: AltaDeProfe, cuerpo: CuerpoTecnico, reglas: Reglas
) -> list[Hallazgo]:
    return [
        *validar_cuerpo_tecnico(alta.rol, alta.roles_en_el_equipo, cuerpo),
        *validar_otros_equipos(alta.equipo, "profe", alta.otras_participaciones, reglas),
        *validar_documento(alta.documento, reglas),
    ]


def validar_edad(alta: AltaDeJugador, reglas: Reglas) -> list[Hallazgo]:
    """INS-02: mayor que la categoría, nunca; menor, según la regla y con aviso."""
    if alta.nacimiento is None:
        return [Hallazgo("error", "INS-02", "Falta la fecha de nacimiento.")]
    primero = alta.anio_torneo - alta.categoria.edad
    ultimo = primero + alta.categoria.anios_nacimiento - 1
    anio = alta.nacimiento.year
    categoria = alta.equipo.categoria
    if anio < primero:
        return [
            Hallazgo(
                "error",
                "INS-02",
                f"Nacido en {anio}: es mayor para {categoria}, que es para nacidos en "
                f"{primero}{' o ' + str(ultimo) if ultimo != primero else ''}.",
            )
        ]
    menor_por = anio - ultimo
    if menor_por <= 0:
        return []
    if not reglas.jugar_en_categoria_mayor:
        return [
            Hallazgo(
                "error",
                "INS-02",
                f"Nacido en {anio}: el reglamento no deja jugar en una categoría mayor.",
            )
        ]
    if menor_por > reglas.aviso_anios_menor:
        return [
            Hallazgo(
                "aviso",
                "INS-02",
                f"Nacido en {anio}: es {menor_por} años menor que {categoria}. Se permite.",
            )
        ]
    return []


def validar_cantidad(alta: AltaDeJugador) -> list[Hallazgo]:
    """INS-03: el máximo no se pasa; por debajo del mínimo, aviso."""
    con_el_nuevo = alta.jugadores_en_el_equipo + 1
    if con_el_nuevo > alta.categoria.max_jugadores:
        return [
            Hallazgo(
                "error",
                "INS-03",
                f"El equipo ya tiene {alta.jugadores_en_el_equipo} jugadores, el máximo.",
            )
        ]
    if con_el_nuevo < alta.categoria.min_jugadores:
        faltan = alta.categoria.min_jugadores - con_el_nuevo
        return [
            Hallazgo(
                "aviso",
                "INS-03",
                f"Faltan {faltan} para el mínimo de {alta.categoria.min_jugadores} jugadores.",
            )
        ]
    return []


def validar_otros_equipos(
    equipo: EquipoRef, rol: Rol, otras: tuple[Participacion, ...], reglas: Reglas
) -> list[Hallazgo]:
    """INS-05 a INS-07: la misma persona en otros equipos."""
    hallazgos: list[Hallazgo] = []
    tambien_dirige: list[str] = []
    for otra in otras:
        if otra.equipo.id == equipo.id:
            regla = "INS-05" if rol == "jugador" else "INS-06"
            hallazgos.append(Hallazgo("error", regla, "Ya está en este equipo."))
        elif rol == "jugador" and otra.rol == "jugador":
            hallazgos.append(_jugador_en_dos_equipos(equipo, otra.equipo, reglas))
        elif rol == "profe" and otra.rol == "profe":
            tambien_dirige.append(otra.equipo.descripcion)
        else:
            hallazgos.append(_jugador_y_profe(otra, reglas))
    if tambien_dirige:
        hallazgos.append(
            Hallazgo(
                "aviso",
                "INS-06",
                f"También dirige {_enumerar(tambien_dirige)}. Esos equipos no juegan a la vez.",
            )
        )
    return hallazgos


def _enumerar(cosas: list[str]) -> str:
    """ "A", "A y B", "A, B y C"."""
    return cosas[0] if len(cosas) == 1 else f"{', '.join(cosas[:-1])} y {cosas[-1]}"


def _jugador_en_dos_equipos(equipo: EquipoRef, otro: EquipoRef, reglas: Reglas) -> Hallazgo:
    ya = f"Ya juega en {otro.descripcion}."
    if reglas.jugador_en_dos_equipos == "nunca":
        return Hallazgo("error", "INS-05", f"{ya} El reglamento no deja jugar en dos equipos.")
    if otro.club != equipo.club:
        return Hallazgo("error", "INS-05", f"{ya} Solo se permite dentro del mismo club.")
    if otro.categoria == equipo.categoria:
        return Hallazgo("error", "INS-05", f"{ya} No se permite en la misma categoría.")
    return Hallazgo(
        "aviso",
        "INS-05",
        f"{ya} Se permite porque es el mismo club y otra categoría. "
        "Esos dos equipos no van a jugar a la vez.",
    )


def _jugador_y_profe(otra: Participacion, reglas: Reglas) -> Hallazgo:
    como = "juega en" if otra.rol == "jugador" else "dirige"
    texto = f"También {como} {otra.equipo.descripcion}."
    if not reglas.jugador_y_profe:
        return Hallazgo(
            "error", "INS-07", f"{texto} El reglamento no deja ser jugador y profe a la vez."
        )
    return Hallazgo("aviso", "INS-07", f"{texto} Esos equipos no juegan a la vez.")


def validar_cuerpo_tecnico(
    rol: str, actuales: tuple[str, ...], cuerpo: CuerpoTecnico
) -> list[Hallazgo]:
    """INS-08: hasta max_por_equipo personas, con roles conocidos y un solo entrenador."""
    if rol not in cuerpo.roles:
        return [
            Hallazgo(
                "error",
                "INS-08",
                f"El rol «{rol}» no existe. Los roles son: {', '.join(cuerpo.roles)}.",
            )
        ]
    if len(actuales) >= cuerpo.max_por_equipo:
        return [
            Hallazgo(
                "error",
                "INS-08",
                f"El cuerpo técnico ya tiene {len(actuales)} personas, el máximo.",
            )
        ]
    if rol == "entrenador" and actuales.count("entrenador") >= cuerpo.max_entrenadores:
        return [Hallazgo("error", "INS-08", "El equipo ya tiene entrenador.")]
    return []


def validar_dorsal(dorsal: int | None, usados: frozenset[int], reglas: Reglas) -> list[Hallazgo]:
    """INS-09: opcional al inscribir (según la regla), único en el equipo."""
    if dorsal is None:
        if reglas.dorsal_obligatorio == "al_inscribir":
            return [Hallazgo("error", "INS-09", "Falta el dorsal.")]
        return [Hallazgo("aviso", "INS-09", "Sin dorsal. Hace falta antes del primer partido.")]
    if not DORSAL_MINIMO <= dorsal <= DORSAL_MAXIMO:
        return [Hallazgo("error", "INS-09", f"El dorsal va de {DORSAL_MINIMO} a {DORSAL_MAXIMO}.")]
    if dorsal in usados:
        return [Hallazgo("error", "INS-09", f"El dorsal {dorsal} ya lo usa otro jugador.")]
    return []


def validar_documento(documento: Documento | None, reglas: Reglas) -> list[Hallazgo]:
    """INS-10: sin documento se puede cargar, con aviso de documento pendiente."""
    if documento is not None:
        return []
    if reglas.ci_obligatorio == "al_inscribir":
        return [Hallazgo("error", "INS-10", "Falta el CI o el pasaporte.")]
    return [
        Hallazgo(
            "aviso",
            "INS-10",
            "Documento pendiente: hace falta el CI o el pasaporte antes del primer partido.",
        )
    ]


def validar_cierre(hoy: date, reglas: Reglas, *, es_organizacion: bool) -> list[Hallazgo]:
    """INS-11: después del cierre de inscripción, solo la organización cambia las listas."""
    cierre = reglas.cierre_inscripcion
    if cierre is None or hoy <= cierre or es_organizacion:
        return []
    return [
        Hallazgo(
            "error",
            "INS-11",
            f"La inscripción cerró el {cierre:%d/%m/%Y}. Solo la organización cambia las listas.",
        )
    ]
