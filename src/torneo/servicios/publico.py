"""Lo que la página pública muestra de los partidos y de los jugadores (T8.10, B7).

Es el único lugar que lee personas para la página pública. De cada jugador sale "Nombre I." y
su dorsal (P65); nunca el CI, la fecha de nacimiento ni el apellido completo. Las vistas
públicas usan solo esto y modelos sin datos personales (tests/torneo/test_publico.py).
"""

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from django.utils import timezone

from torneo.models import CategoriaNivel, Evento, Jugador, Partido, Persona, Torneo
from torneo.presentacion import escudo
from torneo.servicios.partido import resultado_de

TIPOS = {"gol": "Gol", "gol_en_contra": "Gol en contra", "amarilla": "Amarilla", "roja": "Roja"}
_ESTADOS = {"en_juego": "En juego", "jugado": "Terminado"}


def nombre_publico(persona: Persona) -> str:
    """P65: "Juan P." (el primer nombre y la inicial del primer apellido)."""
    nombre = persona.nombres.split()[0] if persona.nombres.split() else ""
    inicial = f" {persona.apellidos.strip()[0].upper()}." if persona.apellidos.strip() else ""
    return f"{nombre}{inicial}"


def _jugador(jugador: Jugador | None) -> dict[str, Any] | None:
    if jugador is None:
        return None
    return {"nombre": nombre_publico(jugador.persona), "dorsal": jugador.dorsal}


@dataclass(frozen=True)
class FilaDePartido:
    pk: int
    categoria: str
    hora: str
    cancha: str
    local: str
    visitante: str
    escudo_local: dict[str, str] | None
    escudo_visitante: dict[str, str] | None
    marcador: tuple[int, int] | None  # solo si empezó
    estado: str  # "", "En juego" o "Terminado"
    nombre: str  # en la eliminación: "Semi 1 de Oro"


def fila_de_partido(partido: Partido) -> FilaDePartido:
    local = partido.local.nombre if partido.local else partido.texto_local
    visitante = partido.visitante.nombre if partido.visitante else partido.texto_visitante
    return FilaDePartido(
        pk=partido.pk,
        categoria=str(partido.categoria),
        hora=timezone.localtime(partido.inicio).strftime("%H:%M") if partido.inicio else "",
        cancha=partido.cancha.nombre if partido.cancha else "",
        local=local,
        visitante=visitante,
        escudo_local=escudo(partido.local) if partido.local else None,
        escudo_visitante=escudo(partido.visitante) if partido.visitante else None,
        marcador=resultado_de(partido).marcador if partido.empezado else None,
        estado=_ESTADOS.get(partido.estado, ""),
        nombre=partido.nombre,
    )


_CON_TODO = (
    "categoria__torneo",
    "local__club",
    "visitante__club",
    "cancha",
)


_COPAS = {"oro": "Copa de Oro", "plata": "Copa de Plata", "bronce": "Copa de Bronce"}


def partidos_de(categoria: CategoriaNivel) -> list[dict[str, Any]]:
    """Los partidos de la categoría por fecha y, en la eliminación, por copa."""
    partidos = (
        categoria.partidos.select_related(*_CON_TODO)
        .prefetch_related("eventos__equipo")
        .order_by("fecha", "inicio", "pk")
    )
    grupos: dict[str, list[FilaDePartido]] = {}
    for p in partidos:
        if p.fase == Partido.Fase.GRUPOS:
            titulo = f"Fecha {p.fecha}" if p.fecha else "Fase de grupos"
        else:
            titulo = _COPAS.get(p.copa, "Eliminación")
        grupos.setdefault(titulo, []).append(fila_de_partido(p))
    return [{"titulo": titulo, "partidos": filas} for titulo, filas in grupos.items()]


def partidos_del_dia(torneo: Torneo, dia: date) -> list[FilaDePartido]:
    desde = timezone.make_aware(datetime.combine(dia, time.min))
    partidos = (
        Partido.objects.filter(
            categoria__torneo=torneo, inicio__gte=desde, inicio__lt=desde + timedelta(days=1)
        )
        .select_related(*_CON_TODO)
        .prefetch_related("eventos__equipo")
        .order_by("inicio", "cancha__codigo")
    )
    return [fila_de_partido(p) for p in partidos]


def ficha_publica(partido: Partido) -> dict[str, Any]:
    eventos = partido.eventos.select_related("equipo", "jugador__persona")
    return {
        "fila": fila_de_partido(partido),
        "resultado": resultado_de(partido),
        "eventos": [
            {
                "tipo": TIPOS[e.tipo],
                "clase": e.tipo,
                "equipo": e.equipo.nombre,
                "quien": _jugador(e.jugador),
            }
            for e in eventos.order_by("creado_en", "pk")
        ],
        "mejor": _jugador(partido.mejor_jugador),
    }


def goleadores(categoria: CategoriaNivel) -> list[dict[str, Any]]:
    """P71: los goles de cada jugador en la categoría (sin los goles en contra)."""
    goles = Counter(
        Evento.objects.filter(
            partido__categoria=categoria, tipo=Evento.Tipo.GOL, jugador__isnull=False
        ).values_list("jugador_id", flat=True)
    )
    jugadores = Jugador.objects.select_related("persona", "equipo").in_bulk(list(goles))
    lista = [
        {
            "nombre": nombre_publico(jugadores[pk].persona),
            "dorsal": jugadores[pk].dorsal,
            "equipo": jugadores[pk].equipo.nombre,
            "goles": cantidad,
        }
        for pk, cantidad in goles.items()
        if pk in jugadores
    ]
    return sorted(lista, key=lambda g: (-g["goles"], g["nombre"]))
