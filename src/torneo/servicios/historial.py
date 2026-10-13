"""Historial del partido (T11.7): cada acción de la ficha deja quién, cuándo y qué valía antes.
Los cambios de horario siguen en Cambio; la ficha y "Más → Historial" muestran los dos."""

from typing import Any

from django.contrib.auth.models import User
from django.utils import timezone

from torneo.models import Cambio, Equipo, Jugador, Partido, Registro, Torneo
from torneo.presentacion import lugar


def registrar(
    partido: Partido,
    usuario: Any,
    que: str,
    *,
    equipo: Equipo | None = None,
    jugador: Jugador | None = None,
    antes: str = "",
    despues: str = "",
) -> Registro:
    return Registro.objects.create(
        partido=partido,
        usuario=usuario if isinstance(usuario, User) else None,
        que=que,
        equipo=equipo if equipo is not None else (jugador.equipo if jugador else None),
        jugador=jugador,
        antes=antes,
        despues=despues,
    )


def _fila(fecha: Any, usuario: Any, que: str, detalle: str, partido: Partido) -> dict[str, Any]:
    local = timezone.localtime(fecha)
    return {
        "fecha": fecha,
        "hora": f"{local:%d/%m %H:%M}",
        "quien": usuario.username if usuario else "",
        "que": que,
        "detalle": detalle,
        "partido": partido,
    }


def _detalle(registro: Registro) -> str:
    partes = []
    if registro.jugador is not None:
        dorsal = registro.jugador.dorsal
        partes.append(f"{dorsal if dorsal is not None else 's/n'} · {registro.jugador.persona}")
    if registro.equipo is not None:
        partes.append(registro.equipo.nombre)
    if registro.antes or registro.despues:
        partes.append(f"{registro.antes or '—'} → {registro.despues or '—'}")
    return " · ".join(partes)


def historial(
    *, partido: Partido | None = None, torneo: Torneo | None = None, limite: int = 200
) -> list[dict[str, Any]]:
    """Lo último primero: las acciones de la ficha y los cambios de horario."""
    registros = Registro.objects.select_related(
        "usuario", "equipo", "jugador__persona", "partido__categoria"
    )
    cambios = Cambio.objects.select_related(
        "usuario", "cancha_antes", "cancha_despues", "partido__categoria"
    )
    if partido is not None:
        registros, cambios = registros.filter(partido=partido), cambios.filter(partido=partido)
    if torneo is not None:
        registros = registros.filter(partido__categoria__torneo=torneo)
        cambios = cambios.filter(partido__categoria__torneo=torneo)
    filas = [
        _fila(r.fecha, r.usuario, r.que, _detalle(r), r.partido) for r in registros[:limite]
    ] + [
        _fila(
            c.fecha,
            c.usuario,
            c.motivo or "Horario",
            f"{lugar(c.inicio_antes, c.cancha_antes.codigo if c.cancha_antes else '')} → "
            f"{lugar(c.inicio_despues, c.cancha_despues.codigo if c.cancha_despues else '')}",
            c.partido,
        )
        for c in cambios[:limite]
    ]
    return sorted(filas, key=lambda f: f["fecha"], reverse=True)[:limite]
