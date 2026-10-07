"""Servicio de inscripción (T2.4): agrega jugadores y profes a un equipo.

Arma la entrada del dominio con lo que hay en la base (dominio.inscripcion), y guarda solo si
no hay errores. Los avisos se devuelven para mostrarlos. Cada alta va en una transacción que
bloquea al equipo, así dos altas a la vez no pasan del máximo.
"""

from dataclasses import dataclass, field
from datetime import date

from django.db import IntegrityError, transaction

from dominio.config import CuerpoTecnico, Reglas
from dominio.documentos import Documento, DocumentoInvalido, normalizar_documento
from dominio.inscripcion import (
    AltaDeJugador,
    AltaDeProfe,
    CategoriaDelEquipo,
    EquipoRef,
    Hallazgo,
    Participacion,
    validar_alta_de_jugador,
    validar_alta_de_profe,
    validar_cierre,
)
from torneo.models import Equipo, Jugador, Persona, Profe


@dataclass(frozen=True)
class DatosPersona:
    """Lo que escribe la organización. El documento va como venga ("1.234.567 lp")."""

    documento: str
    nombres: str
    apellidos: str
    nacimiento: date | None


@dataclass
class Resultado:
    guardado: bool
    hallazgos: list[Hallazgo] = field(default_factory=list)
    registro: Jugador | Profe | None = None

    @property
    def errores(self) -> list[Hallazgo]:
        return [h for h in self.hallazgos if h.nivel == "error"]

    @property
    def avisos(self) -> list[Hallazgo]:
        return [h for h in self.hallazgos if h.nivel == "aviso"]


def equipo_ref(equipo: Equipo) -> EquipoRef:
    categoria = equipo.categoria
    return EquipoRef(equipo.pk, equipo.club.nombre, categoria.categoria, str(categoria))


def _reglas(equipo: Equipo) -> Reglas:
    return Reglas.model_validate(equipo.categoria.torneo.reglas)


@dataclass(frozen=True)
class _Preparado:
    documento: Documento | None
    persona: Persona | None  # la que ya existe con ese documento
    otras: tuple[Participacion, ...]
    hallazgos: tuple[Hallazgo, ...]


def _preparar(datos: DatosPersona, equipo: Equipo, hoy: date, es_organizacion: bool) -> _Preparado:
    hallazgos = list(validar_cierre(hoy, _reglas(equipo), es_organizacion=es_organizacion))
    try:
        documento = normalizar_documento(datos.documento)
    except DocumentoInvalido as error:
        return _Preparado(None, None, (), (*hallazgos, Hallazgo("error", "INS-04", str(error))))

    persona = Persona.objects.filter(clave_documento=documento.clave).first() if documento else None
    otras: tuple[Participacion, ...] = ()
    if persona is not None:
        if (persona.nombres, persona.apellidos, persona.nacimiento) != (
            datos.nombres,
            datos.apellidos,
            datos.nacimiento or persona.nacimiento,
        ):
            hallazgos.append(
                Hallazgo(
                    "aviso",
                    "INS-04",
                    f"Ese documento ya está cargado a nombre de {persona}. "
                    "Se usan los datos guardados.",
                )
            )
        otras = tuple(
            Participacion(equipo_ref(j.equipo), "jugador")
            for j in persona.jugadores.select_related("equipo__club", "equipo__categoria")
        ) + tuple(
            Participacion(equipo_ref(p.equipo), "profe")
            for p in persona.profes.select_related("equipo__club", "equipo__categoria")
        )
    return _Preparado(documento, persona, otras, tuple(hallazgos))


def _hallazgos_de_jugador(
    equipo: Equipo, datos: DatosPersona, dorsal: int | None, preparado: _Preparado
) -> list[Hallazgo]:
    if any(h.regla == "INS-04" and h.nivel == "error" for h in preparado.hallazgos):
        return list(preparado.hallazgos)
    categoria = equipo.categoria
    nacimiento = preparado.persona.nacimiento if preparado.persona else datos.nacimiento
    alta = AltaDeJugador(
        equipo=equipo_ref(equipo),
        categoria=CategoriaDelEquipo(
            categoria.edad,
            categoria.anios_nacimiento,
            categoria.min_jugadores,
            categoria.max_jugadores,
        ),
        anio_torneo=categoria.torneo.anio,
        nacimiento=nacimiento,
        documento=preparado.documento,
        dorsal=dorsal,
        jugadores_en_el_equipo=equipo.jugadores.count(),
        dorsales_en_el_equipo=frozenset(
            d for d in equipo.jugadores.values_list("dorsal", flat=True) if d is not None
        ),
        otras_participaciones=preparado.otras,
    )
    return [*preparado.hallazgos, *validar_alta_de_jugador(alta, _reglas(equipo))]


def _hallazgos_de_profe(equipo: Equipo, rol: str, preparado: _Preparado) -> list[Hallazgo]:
    if any(h.regla == "INS-04" and h.nivel == "error" for h in preparado.hallazgos):
        return list(preparado.hallazgos)
    alta = AltaDeProfe(
        equipo=equipo_ref(equipo),
        rol=rol,
        documento=preparado.documento,
        roles_en_el_equipo=tuple(equipo.profes.values_list("rol", flat=True)),
        otras_participaciones=preparado.otras,
    )
    cuerpo = CuerpoTecnico.model_validate(equipo.categoria.torneo.cuerpo_tecnico)
    return [*preparado.hallazgos, *validar_alta_de_profe(alta, cuerpo, _reglas(equipo))]


def revisar_jugador(
    equipo: Equipo, datos: DatosPersona, dorsal: int | None, *, hoy: date, es_organizacion: bool
) -> list[Hallazgo]:
    """Los hallazgos sin guardar nada: para los avisos en vivo del formulario."""
    preparado = _preparar(datos, equipo, hoy, es_organizacion)
    return _hallazgos_de_jugador(equipo, datos, dorsal, preparado)


def revisar_profe(
    equipo: Equipo, datos: DatosPersona, rol: str, *, hoy: date, es_organizacion: bool
) -> list[Hallazgo]:
    return _hallazgos_de_profe(equipo, rol, _preparar(datos, equipo, hoy, es_organizacion))


def _persona(datos: DatosPersona, preparado: _Preparado) -> Persona:
    if preparado.persona is not None:
        return preparado.persona
    documento = preparado.documento
    return Persona.objects.create(
        tipo_documento=documento.tipo if documento else "",
        documento=documento.texto if documento else "",
        clave_documento=documento.clave if documento else "",
        nombres=datos.nombres.strip(),
        apellidos=datos.apellidos.strip(),
        nacimiento=datos.nacimiento,
    )


_CHOQUE = Hallazgo(
    "error", "", "Alguien cargó a la misma persona o el mismo dorsal recién. Revisa la lista."
)


def agregar_jugador(
    equipo: Equipo, datos: DatosPersona, dorsal: int | None, *, hoy: date, es_organizacion: bool
) -> Resultado:
    try:
        with transaction.atomic():
            bloqueado = (
                Equipo.objects.select_for_update()
                .select_related("club", "categoria__torneo")
                .get(pk=equipo.pk)
            )
            preparado = _preparar(datos, bloqueado, hoy, es_organizacion)
            hallazgos = _hallazgos_de_jugador(bloqueado, datos, dorsal, preparado)
            if any(h.nivel == "error" for h in hallazgos):
                return Resultado(False, hallazgos)
            jugador = Jugador.objects.create(
                persona=_persona(datos, preparado), equipo=bloqueado, dorsal=dorsal
            )
    except IntegrityError:
        return Resultado(False, [_CHOQUE])
    return Resultado(True, hallazgos, jugador)


def agregar_profe(
    equipo: Equipo, datos: DatosPersona, rol: str, *, hoy: date, es_organizacion: bool
) -> Resultado:
    try:
        with transaction.atomic():
            bloqueado = (
                Equipo.objects.select_for_update()
                .select_related("club", "categoria__torneo")
                .get(pk=equipo.pk)
            )
            preparado = _preparar(datos, bloqueado, hoy, es_organizacion)
            hallazgos = _hallazgos_de_profe(bloqueado, rol, preparado)
            if any(h.nivel == "error" for h in hallazgos):
                return Resultado(False, hallazgos)
            profe = Profe.objects.create(
                persona=_persona(datos, preparado), equipo=bloqueado, rol=rol
            )
    except IntegrityError:
        return Resultado(False, [_CHOQUE])
    return Resultado(True, hallazgos, profe)
