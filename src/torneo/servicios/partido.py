"""Cargar un partido desde la mesa (T8.5, B3): empezar, goles y tarjetas, deshacer, W.O.,
penales, mejor jugador y terminar. Cada evento queda con quién lo cargó y cuándo.

El marcador no se guarda: sale de los eventos (dominio.partido). Un partido empezado ya no se
mueve (PRO-10) ni deja rehacer su fixture (FIX-09).
"""

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser, User
from django.db import transaction
from django.utils import timezone

from dominio.config import Reglas
from dominio.partido import Evento as EventoDelDominio
from dominio.partido import Lado, Resultado, ResultadoInvalido, TipoDeEvento, resultado
from torneo.models import Equipo, Evento, Jugador, Partido

Usuario = AbstractBaseUser | AnonymousUser


class NoSePuede(ValueError):
    """La acción no vale para este partido; el mensaje dice por qué."""


def _usuario(usuario: Usuario | None) -> User | None:
    return usuario if isinstance(usuario, User) else None


def _lado(partido: Partido, equipo: Equipo) -> Lado:
    if equipo.pk == partido.local_id:
        return "local"
    if equipo.pk == partido.visitante_id:
        return "visitante"
    raise NoSePuede(f"{equipo.nombre} no juega este partido.")


def resultado_de(partido: Partido) -> Resultado:
    eventos = [
        EventoDelDominio(e.tipo, _lado(partido, e.equipo))  # type: ignore[arg-type]
        for e in partido.eventos.select_related("equipo")
    ]
    penales = None
    if partido.penales_local is not None and partido.penales_visitante is not None:
        penales = (partido.penales_local, partido.penales_visitante)
    return resultado(
        eventos,
        no_se_presento=partido.no_se_presento or None,  # type: ignore[arg-type]
        marcador_wo=Reglas.model_validate(partido.categoria.torneo.reglas).marcador_wo,
        penales=penales,
        eliminacion=partido.fase == Partido.Fase.ELIMINACION,
    )


def empezar(partido: Partido, usuario: Usuario | None) -> None:
    if partido.local_id is None or partido.visitante_id is None:
        raise NoSePuede("Faltan los equipos de este partido: asígnalos antes de empezar.")
    if partido.estado == Partido.Estado.JUGADO:
        raise NoSePuede("El partido ya terminó.")
    partido.estado = Partido.Estado.EN_JUEGO
    if not partido.tiempo:  # T10.9: el inicio real lo marca la mesa
        partido.tiempo = Partido.Tiempo.PRIMER_TIEMPO
        partido.inicio_real = timezone.now()
    partido.save(update_fields=["estado", "tiempo", "inicio_real"])


def avanzar_tiempo(partido: Partido) -> None:
    """T10.9: fin del primer tiempo, y después fin del descanso."""
    ahora = timezone.now()
    if partido.tiempo == Partido.Tiempo.PRIMER_TIEMPO:
        partido.tiempo, partido.fin_primer_tiempo = Partido.Tiempo.DESCANSO, ahora
    elif partido.tiempo == Partido.Tiempo.DESCANSO:
        partido.tiempo, partido.fin_descanso = Partido.Tiempo.SEGUNDO_TIEMPO, ahora
    else:
        raise NoSePuede("No hay otro tiempo: el partido se termina con «Terminar».")
    partido.save(update_fields=["tiempo", "fin_primer_tiempo", "fin_descanso"])


def anotar(
    partido: Partido,
    tipo: TipoDeEvento,
    equipo: Equipo,
    jugador: Jugador | None,
    usuario: Usuario | None,
) -> Evento:
    if not partido.empezado:
        raise NoSePuede("El partido todavía no empezó: tócalo para empezarlo.")
    _lado(partido, equipo)
    if tipo == "gol_en_contra":
        jugador = None  # P72: sin jugador
    if jugador is not None and jugador.equipo_id != equipo.pk:
        raise NoSePuede(f"Ese jugador no juega en {equipo.nombre}.")
    return Evento.objects.create(
        partido=partido, tipo=tipo, equipo=equipo, jugador=jugador, creado_por=_usuario(usuario)
    )


def deshacer(partido: Partido) -> Evento | None:
    """Borra el último evento cargado (el error más común: tocar el botón equivocado)."""
    ultimo = partido.eventos.order_by("-creado_en", "-pk").first()
    if ultimo is not None:
        ultimo.delete()
    return ultimo


def wo(partido: Partido, no_se_presento: Lado, usuario: Usuario | None) -> None:
    """W.O. (P23): el que se presentó gana con el marcador de la regla."""
    if partido.local_id is None or partido.visitante_id is None:
        raise NoSePuede("Faltan los equipos de este partido.")
    partido.no_se_presento = no_se_presento
    partido.estado = Partido.Estado.JUGADO
    partido.tiempo = Partido.Tiempo.TERMINADO
    partido.save(update_fields=["no_se_presento", "estado", "tiempo"])


def penales(partido: Partido, local: int, visitante: int) -> None:
    if partido.fase != Partido.Fase.ELIMINACION:
        raise NoSePuede("Los penales son solo en la eliminación.")
    partido.penales_local, partido.penales_visitante = local, visitante
    partido.save(update_fields=["penales_local", "penales_visitante"])


def mejor_jugador(partido: Partido, jugador: Jugador | None) -> None:
    """P70: lo eligen el árbitro y la mesa; es de uno de los dos equipos."""
    if jugador is not None and jugador.equipo_id not in (partido.local_id, partido.visitante_id):
        raise NoSePuede("El mejor jugador tiene que ser de uno de los dos equipos.")
    partido.mejor_jugador = jugador
    partido.save(update_fields=["mejor_jugador"])


@transaction.atomic
def terminar(partido: Partido, usuario: Usuario | None) -> None:
    if not partido.empezado:
        raise NoSePuede("El partido todavía no empezó.")
    try:
        resultado_de(partido).revisar_para_terminar()
    except ResultadoInvalido as error:
        raise NoSePuede(str(error)) from None
    partido.estado = Partido.Estado.JUGADO
    partido.tiempo, partido.fin_real = Partido.Tiempo.TERMINADO, timezone.now()
    partido.save(update_fields=["estado", "tiempo", "fin_real"])
