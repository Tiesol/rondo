"""Configuración del torneo como datos (SPEC, catálogo de reglas; CONTEXTO, secciones 4 y 9).

Ninguna regla del reglamento vive en el código: llegan en un JSON que se valida acá. Cada
regla dice de dónde sale (sección del contexto o pregunta P#).
"""

from dataclasses import dataclass
from datetime import date, time
from pathlib import Path
from typing import Any, Literal, Self, cast, get_args, get_origin
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.config import JsonDict

NombreNivel = Literal["unico", "inicial", "avanzado"]
Modalidad = Literal["F5", "F7", "F8", "F11"]
DiaSemana = Literal["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
Momento = Literal["al_inscribir", "antes_del_primer_partido"]


class _Estricto(BaseModel):
    """Inmutable y sin campos desconocidos: una clave mal escrita es un error, no se ignora."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class Nivel(_Estricto):
    modalidad: Modalidad  # 4.1, P14, P15
    min: int = Field(ge=1)  # jugadores en la lista (4.1)
    max: int = Field(ge=1)
    min_por_tiempo: int = Field(gt=0)
    convocados_por_partido: int | None = Field(default=None, ge=1)  # F11: 18 de 22 (4.1)

    @model_validator(mode="after")
    def _topes_coherentes(self) -> Self:
        if self.max < self.min:
            raise ValueError(f"max ({self.max}) no puede ser menor que min ({self.min})")
        if self.convocados_por_partido is not None and self.convocados_por_partido > self.max:
            raise ValueError("convocados_por_partido no puede superar max")
        return self


class Categoria(_Estricto):
    nombre: str = Field(min_length=1)
    edad: int = Field(ge=1)  # la N de "Sub N"
    anios_nacimiento: int = Field(default=1, ge=1, le=3)  # Sub 17 abarca dos (4.1)
    genero: Literal["mixto", "F"] = "mixto"
    niveles: dict[NombreNivel, Nivel] = Field(min_length=1)

    @field_validator("niveles")
    @classmethod
    def _unico_va_solo(cls, niveles: dict[NombreNivel, Nivel]) -> dict[NombreNivel, Nivel]:
        if "unico" in niveles and len(niveles) > 1:
            raise ValueError("el nivel unico no se combina con inicial ni avanzado")
        return niveles

    def anios_de_nacimiento(self, anio_torneo: int) -> tuple[int, ...]:
        """CAT-01: año del torneo - N; Sub 17 suma el año siguiente (año - 16)."""
        primero = anio_torneo - self.edad
        return tuple(range(primero, primero + self.anios_nacimiento))


class Partido(_Estricto):
    descanso_min: int = Field(default=5, ge=0)  # 4.4
    cambio_entre_partidos_min: int = Field(default=5, ge=0)  # 4.4, P16


class Cancha(_Estricto):
    codigo: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    mitades: tuple[str, ...] = ()  # C1 se usa entera o en dos mitades (5.1)


class Compatibilidad(_Estricto):
    """Canchas por categoría (manda) o por modalidad (CAT-04)."""

    por_categoria: dict[str, tuple[str, ...]] = {}
    por_modalidad: dict[Modalidad, tuple[str, ...]] = {}


class CuerpoTecnico(_Estricto):
    max_por_equipo: int = Field(default=3, ge=1)  # 4.2, P11
    max_entrenadores: int = Field(default=1, ge=1)  # P40
    roles: tuple[str, ...] = ("entrenador", "asistente", "delegado")  # 4.2


class Torneo(_Estricto):
    nombre: str = Field(min_length=1)
    edicion: int = Field(ge=1)
    anio: int = Field(ge=2000)
    inicio: date  # P12
    fin: date
    zona_horaria: str = "America/La_Paz"

    @field_validator("zona_horaria")
    @classmethod
    def _zona_existe(cls, zona: str) -> str:
        try:
            ZoneInfo(zona)
        except ZoneInfoNotFoundError:
            raise ValueError(f"zona horaria desconocida: {zona}") from None
        return zona

    @model_validator(mode="after")
    def _fechas_en_orden(self) -> Self:
        if self.fin < self.inicio:
            raise ValueError("fin no puede ser anterior a inicio")
        return self


def _regla(
    defecto: Any,
    titulo: str,
    ayuda: str,
    *,
    grupo: str,
    pregunta: str = "",
    regla: str = "",
    unidad: str = "",
    opciones: dict[str, str] | None = None,
    **limites: Any,
) -> Any:
    """Un campo de Reglas con lo que necesita la pantalla: título, ayuda y de dónde sale."""
    extra: JsonDict = {"grupo": grupo, "pregunta": pregunta, "regla": regla, "unidad": unidad}
    if opciones:
        extra["opciones"] = dict(opciones)
    return Field(
        default=defecto, title=titulo, description=ayuda, json_schema_extra=extra, **limites
    )


_MOMENTOS = {
    "al_inscribir": "Al inscribir",
    "antes_del_primer_partido": "Antes del primer partido",
}


class Reglas(_Estricto):
    """Reglas sueltas del reglamento. El valor por defecto es el de la pregunta P# indicada.

    Una regla nueva solo se agrega acá: la pantalla de reglas se arma con describir_reglas().
    """

    jugar_en_categoria_mayor: bool = _regla(
        True,
        "Se puede jugar en una categoría mayor",
        "Un jugador más chico puede inscribirse en una categoría de más edad. "
        "Uno mayor que su categoría no se acepta nunca.",
        grupo="Inscripción",
        pregunta="P6",
        regla="INS-02",
    )
    aviso_anios_menor: int = _regla(
        2,
        "Avisar si es menor por más de",
        "La app avisa cuando un jugador tiene más de estos años menos que su categoría.",
        grupo="Inscripción",
        pregunta="P42",
        regla="INS-02",
        unidad="años",
        ge=0,
    )
    jugador_en_dos_equipos: Literal["mismo_club_otra_categoria", "nunca"] = _regla(
        "mismo_club_otra_categoria",
        "Jugador en dos equipos",
        "Si se permite, esos dos equipos nunca juegan a la vez.",
        grupo="Inscripción",
        pregunta="P7",
        regla="INS-05",
        opciones={
            "mismo_club_otra_categoria": "Solo del mismo club, en otra categoría",
            "nunca": "Nunca",
        },
    )
    jugador_y_profe: bool = _regla(
        True,
        "Jugador en un equipo y profe en otro",
        "Por ejemplo, un Sub 17 que dirige a un Sub 6. Esos equipos no juegan a la vez.",
        grupo="Inscripción",
        pregunta="P37",
        regla="INS-07",
    )
    dorsal_obligatorio: Momento = _regla(
        "antes_del_primer_partido",
        "El dorsal es obligatorio",
        "Hasta entonces, la lista se guarda con un aviso.",
        grupo="Inscripción",
        pregunta="P9",
        regla="INS-09",
        opciones=_MOMENTOS,
    )
    ci_obligatorio: Momento = _regla(
        "antes_del_primer_partido",
        "El CI es obligatorio",
        "Hasta entonces, el jugador queda con el aviso de documento pendiente.",
        grupo="Inscripción",
        pregunta="P39",
        regla="INS-10",
        opciones=_MOMENTOS,
    )
    cierre_inscripcion: date | None = _regla(
        None,
        "Cierre de la inscripción",
        "Después de esta fecha, solo la organización cambia las listas. Vacío: sin cierre.",
        grupo="Inscripción",
        pregunta="P4",
        regla="INS-11",
    )
    mismo_club_fecha_1: bool = _regla(
        True,
        "Mismo club, primero entre ellos",
        "Dos equipos del mismo club en un grupo se enfrentan en la fecha 1.",
        grupo="Fixture",
        pregunta="P24",
        regla="FIX-05",
    )
    sorteo_separa_clubes: bool = _regla(
        True,
        "El sorteo separa a los clubes",
        "Las series se sortean poniendo a los equipos de un mismo club en series distintas, "
        "cuando se puede.",
        grupo="Fixture",
        pregunta="P45",
        regla="FIX-06",
    )
    rehacer_fixture: bool = _regla(
        True,
        "Rehacer el fixture de una categoría",
        "Mientras la categoría no tenga partidos jugados, se puede rehacer su fixture y "
        "reprogramar solo esa categoría.",
        grupo="Fixture",
        pregunta="P44",
        regla="FIX-09",
    )
    turnos_libres_mismo_dia: int = _regla(
        1,
        "Turnos libres entre dos partidos del mismo día",
        "Si un equipo juega dos veces el mismo día, cuántos turnos quedan libres en medio.",
        grupo="Programación",
        pregunta="P17",
        regla="PRO-04",
        unidad="turnos",
        ge=0,
    )
    max_partidos_por_dia: int = _regla(
        2,
        "Partidos por día de un equipo, como máximo",
        "Un equipo nunca juega más partidos que estos en un mismo día.",
        grupo="Programación",
        pregunta="P47",
        regla="PRO-04",
        unidad="partidos",
        ge=1,
    )
    profe_minutos_cambio_de_cancha: int = _regla(
        10,
        "Minutos de un profe para cambiar de cancha",
        "Entre el final de un partido y el inicio del siguiente, cuando es en otra cancha.",
        grupo="Programación",
        pregunta="P35",
        regla="PRO-05",
        unidad="min",
        ge=0,
    )
    orden_de_fechas: Literal["dura", "blanda"] = _regla(
        "dura",
        "Orden de las fechas",
        "Los partidos de cada equipo van en el orden de las fechas.",
        grupo="Programación",
        pregunta="P19",
        regla="PRO-08",
        opciones={"dura": "Siempre en orden", "blanda": "En orden, salvo que un cambio obligue"},
    )
    eliminacion_desde_fin_de_semana: int = _regla(
        5,
        "La eliminación empieza el fin de semana",
        "El número del fin de semana (1 es el primero) desde el que se juegan semis y finales.",
        grupo="Programación",
        pregunta="P33",
        regla="PRO-09",
        ge=1,
    )
    propuestas_reprogramacion: int = _regla(
        3,
        "Propuestas al reprogramar",
        "Cuántas opciones distintas ofrece la app cuando hay que mover un partido.",
        grupo="Programación",
        regla="PRO-13",
        ge=1,
        le=5,
    )
    marcador_wo: tuple[int, int] = _regla(
        (3, 0),
        "Marcador del W.O.",
        "El resultado que se carga cuando un equipo no se presenta.",
        grupo="Resultados",
        pregunta="P23",
    )


TipoDeRegla = Literal["si_no", "numero", "opcion", "fecha", "par"]


@dataclass(frozen=True)
class DescripcionRegla:
    """Lo que la pantalla necesita para mostrar y editar una regla."""

    nombre: str
    titulo: str
    ayuda: str
    grupo: str
    tipo: TipoDeRegla
    defecto: Any
    pregunta: str = ""
    regla: str = ""
    unidad: str = ""
    minimo: int | None = None
    maximo: int | None = None
    opciones: tuple[tuple[str, str], ...] = ()


def _tipo(nombre: str, anotacion: Any) -> TipoDeRegla:
    if anotacion is bool:
        return "si_no"
    if anotacion is int:
        return "numero"
    if get_origin(anotacion) is Literal:
        return "opcion"
    if anotacion == date | None:
        return "fecha"
    if anotacion == tuple[int, int]:
        return "par"
    raise TypeError(f"La regla {nombre} tiene un tipo que la pantalla no sabe mostrar")


def describir_reglas(modelo: type[Reglas] = Reglas) -> list[DescripcionRegla]:
    """Las reglas en el orden del modelo, con todo lo necesario para la pantalla."""
    descripciones = []
    for nombre, campo in modelo.model_fields.items():
        extra = campo.json_schema_extra if isinstance(campo.json_schema_extra, dict) else {}
        tipo = _tipo(nombre, campo.annotation)
        limites = {
            clave: getattr(m, clave)
            for m in campo.metadata
            for clave in ("ge", "gt", "le")
            if hasattr(m, clave)
        }
        minimo = limites.get("ge", limites["gt"] + 1 if "gt" in limites else None)
        etiquetas = cast(dict[str, str], extra.get("opciones", {}))
        opciones = (
            tuple((valor, etiquetas.get(valor, valor)) for valor in get_args(campo.annotation))
            if tipo == "opcion"
            else ()
        )
        descripciones.append(
            DescripcionRegla(
                nombre=nombre,
                titulo=campo.title or nombre,
                ayuda=campo.description or "",
                grupo=str(extra.get("grupo", "")),
                tipo=tipo,
                defecto=campo.default,
                pregunta=str(extra.get("pregunta", "")),
                regla=str(extra.get("regla", "")),
                unidad=str(extra.get("unidad", "")),
                minimo=minimo,
                maximo=limites.get("le"),
                opciones=opciones,
            )
        )
    return descripciones


class ConfigTorneo(_Estricto):
    torneo: Torneo
    partido: Partido = Partido()
    categorias: tuple[Categoria, ...] = Field(min_length=1)
    canchas: tuple[Cancha, ...] = Field(min_length=1)
    compatibilidad: Compatibilidad
    franjas: dict[DiaSemana, tuple[time, time]]  # 4.3
    cuerpo_tecnico: CuerpoTecnico = CuerpoTecnico()
    reglas: Reglas = Reglas()

    @field_validator("franjas")
    @classmethod
    def _franjas_en_orden(
        cls, franjas: dict[DiaSemana, tuple[time, time]]
    ) -> dict[DiaSemana, tuple[time, time]]:
        for dia, (inicio, fin) in franjas.items():
            if fin <= inicio:
                raise ValueError(f"la franja del {dia} termina antes de empezar")
        return franjas

    @model_validator(mode="after")
    def _referencias_validas(self) -> Self:
        nombres = [c.nombre for c in self.categorias]
        if len(set(nombres)) != len(nombres):
            raise ValueError("hay categorías con el nombre repetido")
        codigos = {c.codigo for c in self.canchas} | {m for c in self.canchas for m in c.mitades}
        usadas = [
            *self.compatibilidad.por_categoria.values(),
            *self.compatibilidad.por_modalidad.values(),
        ]
        desconocidas = sorted({cancha for lista in usadas for cancha in lista} - codigos)
        if desconocidas:
            raise ValueError(
                f"compatibilidad con canchas que no existen: {', '.join(desconocidas)}"
            )
        sin_categoria = sorted(set(self.compatibilidad.por_categoria) - set(nombres))
        if sin_categoria:
            raise ValueError(
                f"compatibilidad con categorías que no existen: {', '.join(sin_categoria)}"
            )
        return self

    def categoria(self, nombre: str) -> Categoria:
        return next(c for c in self.categorias if c.nombre == nombre)

    def minutos_partido(self, nivel: Nivel) -> int:
        return minutos_partido(nivel.min_por_tiempo, self.partido)

    def minutos_turno(self, nivel: Nivel) -> int:
        return minutos_turno(nivel.min_por_tiempo, self.partido)


def minutos_partido(min_por_tiempo: int, partido: Partido) -> int:
    """CAT-03: dos tiempos más el descanso."""
    return 2 * min_por_tiempo + partido.descanso_min


def minutos_turno(min_por_tiempo: int, partido: Partido) -> int:
    """CAT-03: el partido más el cambio entre partidos (40, 50, 60 o 70 en 2026)."""
    return minutos_partido(min_por_tiempo, partido) + partido.cambio_entre_partidos_min


def cargar_config(archivo: Path) -> ConfigTorneo:
    return ConfigTorneo.model_validate_json(archivo.read_text())
