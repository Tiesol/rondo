"""La planilla del partido (T11.8, P9): quiénes juegan y con qué dorsal en este partido.

El dorsal es del partido: se propone el del partido anterior del jugador o, si no hay, el
habitual del plantel. Dos jugadores del mismo equipo no repiten dorsal en un partido (la base
no lo deja). Convocar a un suspendido pide confirmación.
"""

from typing import Any

from django.db import IntegrityError, transaction

from torneo.models import Convocado, Equipo, Jugador, Partido
from torneo.servicios.historial import registrar
from torneo.servicios.suspensiones import suspendidos_en


class NoSePuede(ValueError):
    """No se guardó; el mensaje dice por qué."""


class PideConfirmar(ValueError):
    """Se guarda solo si la organización lo confirma; el mensaje dice qué."""


def _lado(partido: Partido, equipo: Equipo) -> str:
    if equipo.pk == partido.local_id:
        return "local"
    if equipo.pk == partido.visitante_id:
        return "visitante"
    raise NoSePuede(f"{equipo.nombre} no juega este partido.")


def dorsal_sugerido(partido: Partido, jugador: Jugador) -> int | None:
    """El dorsal con el que jugó su último partido anterior a este; si no, el habitual."""
    anteriores = Convocado.objects.filter(jugador=jugador, dorsal__isnull=False).exclude(
        partido=partido
    )
    if partido.inicio is not None:
        anteriores = anteriores.filter(partido__inicio__lt=partido.inicio)
    elif partido.fecha is not None:
        anteriores = anteriores.filter(partido__fecha__lt=partido.fecha)
    ultimo = anteriores.order_by("-partido__inicio", "-partido__fecha", "-pk").first()
    return ultimo.dorsal if ultimo is not None else jugador.dorsal


def _nombre(jugador: Jugador) -> str:
    return f"{jugador.persona.nombres} {jugador.persona.apellidos[:1]}.".strip()


@transaction.atomic
def guardar_planilla(
    partido: Partido,
    equipo: Equipo,
    juegan: dict[int, int | None],
    usuario: Any,
    *,
    confirmado: bool = False,
    entrenador: bool | None = None,
) -> None:
    """`juegan` es {pk del jugador: dorsal en este partido}; los demás del equipo no juegan."""
    lado = _lado(partido, equipo)
    plantel = {j.pk: j for j in equipo.jugadores.select_related("persona")}
    if ajenos := set(juegan) - set(plantel):
        raise NoSePuede(f"{len(ajenos)} jugador(es) no son de {equipo.nombre}.")
    por_dorsal: dict[int, list[Jugador]] = {}
    for pk, dorsal in juegan.items():
        if dorsal is not None:
            if not 1 <= dorsal <= 99:
                raise NoSePuede("El dorsal va de 1 a 99.")
            por_dorsal.setdefault(dorsal, []).append(plantel[pk])
    for dorsal, quienes in sorted(por_dorsal.items()):
        if len(quienes) > 1:
            raise NoSePuede(f"El {dorsal} está repetido: {', '.join(map(_nombre, quienes))}.")

    actuales = {c.jugador_id: c for c in partido.convocados.filter(equipo=equipo)}
    nuevos = set(juegan) - set(actuales)
    suspendidos = {j.pk: motivo for j, motivo in suspendidos_en(partido)}
    if not confirmado and (en_falta := [pk for pk in nuevos if pk in suspendidos]):
        jugador = plantel[en_falta[0]]
        raise PideConfirmar(f"{_nombre(jugador)} está suspendido: {suspendidos[jugador.pk]}.")

    for pk, convocado in actuales.items():
        if pk not in juegan:
            convocado.delete()
            registrar(partido, usuario, "No juega", jugador=plantel.get(pk))
    # Primero se liberan los dorsales que cambian, así dos jugadores pueden intercambiarlos.
    cambian = [c for pk, c in actuales.items() if pk in juegan and c.dorsal != juegan[pk]]
    Convocado.objects.filter(pk__in=[c.pk for c in cambian]).update(dorsal=None)
    try:
        for convocado in cambian:
            antes = "" if convocado.dorsal is None else str(convocado.dorsal)
            convocado.dorsal = juegan[convocado.jugador_id]
            convocado.save(update_fields=["dorsal"])
            despues = "" if convocado.dorsal is None else str(convocado.dorsal)
            jugador = plantel[convocado.jugador_id]
            registrar(partido, usuario, "Dorsal", jugador=jugador, antes=antes, despues=despues)
        for pk in nuevos:
            Convocado.objects.create(
                partido=partido, equipo=equipo, jugador=plantel[pk], dorsal=juegan[pk]
            )
            registrar(
                partido,
                usuario,
                "Juega",
                jugador=plantel[pk],
                despues="" if juegan[pk] is None else str(juegan[pk]),
            )
    except IntegrityError:
        raise NoSePuede("Alguien cambió la planilla recién. Vuelve a cargarla.") from None
    if entrenador is not None:
        setattr(partido, f"entrenador_{lado}", entrenador)
        partido.save(update_fields=[f"entrenador_{lado}"])


def todos(partido: Partido, equipo: Equipo) -> dict[int, int | None]:
    """Todo el plantel menos los suspendidos, con el dorsal sugerido (sin repetir)."""
    suspendidos = {j.pk for j, _ in suspendidos_en(partido)}
    juegan: dict[int, int | None] = {
        c.jugador_id: c.dorsal for c in partido.convocados.filter(equipo=equipo)
    }
    usados = {d for d in juegan.values() if d is not None}
    for jugador in equipo.jugadores.order_by("dorsal", "pk"):
        if jugador.pk in juegan or jugador.pk in suspendidos:
            continue
        dorsal = dorsal_sugerido(partido, jugador)
        juegan[jugador.pk] = dorsal if dorsal not in usados else None
        if dorsal is not None:
            usados.add(dorsal)
    return juegan


def asegurar_convocado(partido: Partido, jugador: Jugador, usuario: Any) -> Convocado:
    """Un evento de alguien que no estaba en la planilla lo suma (con su dorsal sugerido, si
    está libre)."""
    convocado = partido.convocados.filter(jugador=jugador).first()
    if convocado is not None:
        return convocado
    dorsal = dorsal_sugerido(partido, jugador)
    if (
        dorsal is not None
        and partido.convocados.filter(equipo_id=jugador.equipo_id, dorsal=dorsal).exists()
    ):
        dorsal = None
    convocado = Convocado.objects.create(
        partido=partido, equipo_id=jugador.equipo_id, jugador=jugador, dorsal=dorsal
    )
    registrar(partido, usuario, "Juega", jugador=jugador, despues=str(dorsal or ""))
    return convocado


def cambiar_dorsal(partido: Partido, jugador: Jugador, dorsal: int | None, usuario: Any) -> None:
    """El dorsal de este partido (T10.11 y T11.8); el habitual del plantel no cambia."""
    if jugador.equipo_id not in (partido.local_id, partido.visitante_id):
        raise NoSePuede("Ese jugador no juega este partido.")
    if dorsal is not None and not 1 <= dorsal <= 99:
        raise NoSePuede("El dorsal va de 1 a 99.")
    convocado = asegurar_convocado(partido, jugador, usuario)
    if dorsal is not None:
        otro = (
            partido.convocados.filter(equipo_id=jugador.equipo_id, dorsal=dorsal)
            .exclude(pk=convocado.pk)
            .select_related("jugador__persona")
            .first()
        )
        if otro is not None:
            raise NoSePuede(f"El {dorsal} ya lo tiene {_nombre(otro.jugador)}.")
    antes = "" if convocado.dorsal is None else str(convocado.dorsal)
    convocado.dorsal = dorsal
    convocado.save(update_fields=["dorsal"])
    registrar(
        partido,
        usuario,
        "Dorsal",
        jugador=jugador,
        antes=antes,
        despues="" if dorsal is None else str(dorsal),
    )


def dorsales_del_partido(partido: Partido) -> dict[int, int | None]:
    """{pk del jugador: dorsal en este partido}, para mostrar los eventos."""
    return dict(partido.convocados.values_list("jugador_id", "dorsal"))
