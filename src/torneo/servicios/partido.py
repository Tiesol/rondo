"""Cargar un partido desde la mesa (T8.5, B3): empezar, goles y tarjetas, deshacer, W.O.,
penales, mejor jugador y terminar. Cada evento queda con quién lo cargó y cuándo.

El marcador no se guarda: sale de los eventos (dominio.partido). Un partido empezado ya no se
mueve (PRO-10) ni deja rehacer su fixture (FIX-09).
"""

from datetime import datetime, timedelta
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser, User
from django.db import transaction
from django.utils import timezone

from dominio.config import Reglas
from dominio.partido import Evento as EventoDelDominio
from dominio.partido import Lado, Resultado, ResultadoInvalido, TipoDeEvento, resultado
from dominio.penales import EstadoDePenales, Tiro, estado_de_penales
from torneo.models import Cambio, Equipo, Evento, Jugador, Partido, Penal, Torneo
from torneo.servicios.historial import registrar
from torneo.servicios.planilla import asegurar_convocado

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


def _reglas_de(partido: Partido) -> Reglas:
    return Reglas.model_validate(partido.categoria.torneo.reglas)


def estado_penales(partido: Partido) -> EstadoDePenales:
    """La tanda cargada tiro por tiro (T11.13)."""
    tiros: list[Tiro] = [
        (_lado(partido, t.equipo), t.convirtio) for t in partido.tiros.select_related("equipo")
    ]
    return estado_de_penales(tiros, por_equipo=_reglas_de(partido).penales_por_equipo)


def resultado_de(partido: Partido) -> Resultado:
    eventos = [
        EventoDelDominio(e.tipo, _lado(partido, e.equipo))  # type: ignore[arg-type]
        for e in partido.eventos.select_related("equipo")
    ]
    penales = None
    if partido.tiros.exists():  # T11.13: tiro por tiro manda sobre el atajo
        tanda = estado_penales(partido)
        penales = (tanda.local, tanda.visitante)
    elif partido.penales_local is not None and partido.penales_visitante is not None:
        penales = (partido.penales_local, partido.penales_visitante)
    return resultado(
        eventos,
        no_se_presento=partido.no_se_presento or None,  # type: ignore[arg-type]
        marcador_wo=Reglas.model_validate(partido.categoria.torneo.reglas).marcador_wo,
        penales=penales,
        eliminacion=partido.fase == Partido.Fase.ELIMINACION,
    )


def minuto_actual(partido: Partido) -> int | None:
    """T11.10: el minuto en curso, seguido entre tiempos (con 20 por tiempo, el 2.º empieza en
    el 21). En el descanso, el último del primer tiempo. Sin reloj, ninguno."""
    ahora = timezone.now()
    por_tiempo = partido.categoria.min_por_tiempo
    if partido.tiempo == Partido.Tiempo.PRIMER_TIEMPO and partido.inicio_real:
        return int((ahora - partido.inicio_real).total_seconds() // 60) + 1
    if partido.tiempo == Partido.Tiempo.DESCANSO:
        return por_tiempo
    if partido.tiempo == Partido.Tiempo.SEGUNDO_TIEMPO and partido.fin_descanso:
        return por_tiempo + int((ahora - partido.fin_descanso).total_seconds() // 60) + 1
    return None


def fin_esperado(partido: Partido) -> datetime | None:
    """Cuándo debería terminar, según lo que marcó la mesa (T11.11 y T11.12, P82): con el 2.º
    tiempo empezado, su inicio más los minutos del tiempo; si no, desde el inicio real."""
    por_tiempo = timedelta(minutes=partido.categoria.min_por_tiempo)
    if partido.tiempo == Partido.Tiempo.SEGUNDO_TIEMPO and partido.fin_descanso:
        return partido.fin_descanso + por_tiempo
    if partido.tiempo == Partido.Tiempo.DESCANSO and partido.fin_primer_tiempo:
        descanso = timedelta(minutes=partido.categoria.torneo.descanso_min)
        return partido.fin_primer_tiempo + descanso + por_tiempo
    if partido.inicio_real:
        return partido.inicio_real + timedelta(minutes=partido.categoria.minutos_partido)
    return None


def olvidado_desde(partido: Partido, ahora: datetime | None = None) -> datetime | None:
    """T13.11: el final esperado de un partido que sigue en juego y ya lo pasó por más que el
    margen de la regla; si no, None."""
    if partido.estado != Partido.Estado.EN_JUEGO:
        return None
    fin = fin_esperado(partido)
    margen = timedelta(minutes=_reglas_de(partido).cierre_automatico_min)
    if fin is None or (ahora or timezone.now()) < fin + margen:
        return None
    return fin


def cerrar_olvidados(torneo: Torneo, ahora: datetime | None = None) -> int:
    """T11.12 (P82): los partidos en juego pasado su final esperado más `cierre_automatico_min`
    se cierran con el marcador que tenían y la marca "cerrado automáticamente". Corre perezoso
    (al abrir Hoy, la ficha o la página pública) y con un comando para un cron."""
    reglas = Reglas.model_validate(torneo.reglas)
    if not reglas.cierre_automatico:  # T13.11 (P82): "no se cierra sola"
        return 0
    ahora = ahora or timezone.now()
    margen = timedelta(minutes=reglas.cierre_automatico_min)
    cerrados = 0
    for partido in Partido.objects.filter(
        categoria__torneo=torneo, estado=Partido.Estado.EN_JUEGO
    ).select_related("categoria__torneo"):
        fin = fin_esperado(partido)
        if fin is None or ahora < fin + margen:
            continue
        partido.estado, partido.tiempo = Partido.Estado.JUGADO, Partido.Tiempo.TERMINADO
        partido.fin_real, partido.cerrado_automaticamente = fin, True
        partido.save(update_fields=["estado", "tiempo", "fin_real", "cerrado_automaticamente"])
        registrar(partido, None, "Cerrado automáticamente")
        cerrados += 1
    return cerrados


def marcar_revisado(partido: Partido, usuario: Usuario | None) -> None:
    partido.cerrado_automaticamente = False
    partido.save(update_fields=["cerrado_automaticamente"])
    registrar(partido, usuario, "Revisado")


def corregir_minuto(evento: Evento, minuto: int | None, usuario: Usuario | None) -> None:
    antes = "" if evento.minuto is None else f"{evento.minuto}'"
    evento.minuto = minuto
    evento.save(update_fields=["minuto"])
    registrar(
        evento.partido,
        usuario,
        "Minuto",
        equipo=evento.equipo,
        jugador=evento.jugador,
        antes=antes,
        despues="" if minuto is None else f"{minuto}'",
    )


def borrar_evento(evento: Evento, usuario: Usuario | None) -> None:
    """Cualquier evento, también de un partido terminado (T11.10), con su historial."""
    registrar(
        evento.partido,
        usuario,
        f"Borró: {evento.get_tipo_display()}",
        equipo=evento.equipo,
        jugador=evento.jugador,
    )
    evento.delete()


HORAS = {
    "inicio_real": "Inicio",
    "fin_primer_tiempo": "Fin del 1.er tiempo",
    "fin_descanso": "Inicio del 2.º tiempo",
    "fin_real": "Final",
}


def corregir_horas(partido: Partido, horas: dict[str, Any], usuario: Usuario | None) -> None:
    """T11.10: las horas reales del partido se corrigen, con su historial."""
    for campo, nueva in horas.items():
        if campo not in HORAS:
            continue
        vieja = getattr(partido, campo)
        if vieja == nueva:
            continue
        setattr(partido, campo, nueva)
        registrar(
            partido,
            usuario,
            "Horas",
            antes=f"{HORAS[campo]} {timezone.localtime(vieja):%H:%M}" if vieja else "",
            despues=f"{HORAS[campo]} {timezone.localtime(nueva):%H:%M}" if nueva else "",
        )
    partido.save(update_fields=list(HORAS))


def reprogramar_en_juego(partido: Partido, usuario: Usuario | None) -> None:
    """B3 (fase 12): un partido que estaba en juego cuando se suspendió el día y la organización
    decide reprogramarlo. Vuelve a "sin programar" y empieza de nuevo: los goles y tarjetas
    cargados se borran, y todo queda en el historial."""
    if partido.estado != Partido.Estado.EN_JUEGO:
        raise NoSePuede("Solo se reprograma un partido que está en juego.")
    local, visitante = resultado_de(partido).marcador
    registrar(partido, usuario, "Reprogramado en juego", despues=f"marcador {local} a {visitante}")
    for evento in list(partido.eventos.select_related("equipo", "jugador")):
        borrar_evento(evento, usuario)
    partido.tiros.all().delete()
    Cambio.objects.create(
        partido=partido,
        cancha_antes=partido.cancha,
        inicio_antes=partido.inicio,
        usuario=usuario if isinstance(usuario, User) else None,
        motivo="Reprogramado (estaba en juego)",
    )
    partido.estado, partido.tiempo = Partido.Estado.PENDIENTE, Partido.Tiempo.SIN_EMPEZAR
    partido.cancha = partido.inicio = None
    partido.inicio_real = partido.fin_primer_tiempo = partido.fin_descanso = None
    partido.fin_real = partido.mejor_jugador = None
    partido.penales_local = partido.penales_visitante = None
    partido.save()


def quitar_wo(partido: Partido, usuario: Usuario | None) -> None:
    if not partido.no_se_presento:
        raise NoSePuede("Este partido no tiene W.O.")
    ausente = partido.local if partido.no_se_presento == "local" else partido.visitante
    partido.no_se_presento = ""
    if partido.inicio_real is None and not partido.eventos.exists():
        partido.tiempo = Partido.Tiempo.SIN_EMPEZAR
        partido.estado = Partido.Estado.PROGRAMADO if partido.inicio else Partido.Estado.PENDIENTE
    partido.save(update_fields=["no_se_presento", "tiempo", "estado"])
    registrar(partido, usuario, "Quitó el W.O.", equipo=ausente)


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
    registrar(partido, usuario, "Empezó el partido")


def avanzar_tiempo(partido: Partido, usuario: Usuario | None = None) -> None:
    """T10.9: fin del primer tiempo, y después fin del descanso."""
    ahora = timezone.now()
    if partido.tiempo == Partido.Tiempo.PRIMER_TIEMPO:
        partido.tiempo, partido.fin_primer_tiempo = Partido.Tiempo.DESCANSO, ahora
        que = "Fin del 1.er tiempo"
    elif partido.tiempo == Partido.Tiempo.DESCANSO:
        partido.tiempo, partido.fin_descanso = Partido.Tiempo.SEGUNDO_TIEMPO, ahora
        que = "Empezó el 2.º tiempo"
    else:
        raise NoSePuede("No hay otro tiempo: el partido se termina con «Terminar».")
    partido.save(update_fields=["tiempo", "fin_primer_tiempo", "fin_descanso"])
    registrar(partido, usuario, que)


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
    if jugador is not None and jugador.equipo_id != equipo.pk:
        raise NoSePuede(f"Ese jugador no juega en {equipo.nombre}.")
    if jugador is not None:
        asegurar_convocado(partido, jugador, usuario)  # T11.8: si no estaba en la planilla
    evento = Evento.objects.create(
        partido=partido,
        tipo=tipo,
        equipo=equipo,
        jugador=jugador,
        creado_por=_usuario(usuario),
        minuto=minuto_actual(partido),
    )
    registrar(partido, usuario, evento.get_tipo_display(), equipo=equipo, jugador=jugador)
    return evento


def deshacer(partido: Partido, usuario: Usuario | None = None) -> Evento | None:
    """Borra el último evento cargado (el error más común: tocar el botón equivocado)."""
    ultimo = (
        partido.eventos.select_related("equipo", "jugador").order_by("-creado_en", "-pk").first()
    )
    if ultimo is not None:
        registrar(
            partido,
            usuario,
            f"Borró: {ultimo.get_tipo_display()}",
            equipo=ultimo.equipo,
            jugador=ultimo.jugador,
        )
        ultimo.delete()
    return ultimo


def wo(partido: Partido, no_se_presento: Lado, usuario: Usuario | None) -> None:
    """W.O. (P23): el que se presentó gana con el marcador de la regla."""
    if partido.local_id is None or partido.visitante_id is None:
        raise NoSePuede("Faltan los equipos de este partido.")
    # Revisión del bloque A: la ficha esconde el botón, pero una pestaña vieja o un doble toque
    # no pueden pisar un partido empezado o terminado.
    if partido.empezado:
        raise NoSePuede("El partido ya empezó: el W.O. es para un equipo que no se presentó.")
    partido.no_se_presento = no_se_presento
    partido.estado = Partido.Estado.JUGADO
    partido.tiempo = Partido.Tiempo.TERMINADO
    partido.save(update_fields=["no_se_presento", "estado", "tiempo"])
    ausente = partido.local if no_se_presento == "local" else partido.visitante
    registrar(partido, usuario, "W.O.: no se presentó", equipo=ausente)


def _penales_texto(partido: Partido) -> str:
    if partido.penales_local is None or partido.penales_visitante is None:
        return ""
    return f"{partido.penales_local} a {partido.penales_visitante}"


def patear(
    partido: Partido,
    equipo: Equipo,
    convirtio: bool,
    usuario: Usuario | None,
    jugador: Jugador | None = None,
) -> Penal:
    """Un tiro de la tanda (T11.13, P83). Con ganador, la tanda terminó."""
    if partido.fase != Partido.Fase.ELIMINACION:
        raise NoSePuede("Los penales son solo en la eliminación.")
    if partido.local_id is None or partido.visitante_id is None:
        raise NoSePuede("Faltan los equipos de este partido.")
    _lado(partido, equipo)
    if estado_penales(partido).ganador is not None:
        raise NoSePuede("Los penales ya tienen ganador. Deshaz el último si hubo un error.")
    tiro = Penal.objects.create(
        partido=partido,
        equipo=equipo,
        jugador=jugador,
        convirtio=convirtio,
        creado_por=_usuario(usuario),
    )
    que = "Penal convertido" if convirtio else "Penal errado"
    registrar(partido, usuario, que, equipo=equipo, jugador=jugador)
    return tiro


def deshacer_penal(partido: Partido, usuario: Usuario | None) -> None:
    ultimo = partido.tiros.select_related("equipo").order_by("-creado_en", "-pk").first()
    if ultimo is None:
        raise NoSePuede("No hay penales para deshacer.")
    registrar(partido, usuario, "Borró un penal", equipo=ultimo.equipo, jugador=ultimo.jugador)
    ultimo.delete()


def penales(partido: Partido, local: int, visitante: int, usuario: Usuario | None = None) -> None:
    """El atajo (P83): solo el resultado final de la tanda."""
    if partido.fase != Partido.Fase.ELIMINACION:
        raise NoSePuede("Los penales son solo en la eliminación.")
    if partido.tiros.exists():
        raise NoSePuede("Los penales ya se cargan tiro por tiro: deshazlos para usar el atajo.")
    antes = _penales_texto(partido)
    partido.penales_local, partido.penales_visitante = local, visitante
    partido.save(update_fields=["penales_local", "penales_visitante"])
    registrar(partido, usuario, "Penales", antes=antes, despues=_penales_texto(partido))


def mejor_jugador(
    partido: Partido, jugador: Jugador | None, usuario: Usuario | None = None
) -> None:
    """P70: lo eligen el árbitro y la mesa; es de uno de los dos equipos."""
    if jugador is not None and jugador.equipo_id not in (partido.local_id, partido.visitante_id):
        raise NoSePuede("El mejor jugador tiene que ser de uno de los dos equipos.")
    partido.mejor_jugador = jugador
    partido.save(update_fields=["mejor_jugador"])
    registrar(partido, usuario, "Mejor jugador", jugador=jugador)


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
    registrar(partido, usuario, "Terminó el partido")
