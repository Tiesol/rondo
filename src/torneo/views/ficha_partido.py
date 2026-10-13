"""La ficha del partido para la mesa (T8.6, B3): se carga desde el celular durante el partido.

Botones grandes "Gol", "Amarilla" y "Roja": cada uno abre la lista del equipo, con dorsal y
nombre. Cada acción es un POST que vuelve a la ficha (funciona sin JavaScript). Muestra
nombres de jugadores: solo para quien carga resultados (organización y mesa, P64).
"""

from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from dominio.config import Reglas
from torneo.models import Equipo, Jugador, Partido
from torneo.permisos import requiere
from torneo.presentacion import escudo
from torneo.servicios import partido as servicio
from torneo.servicios.partido import NoSePuede
from torneo.servicios.suspensiones import (
    marcar_multa,
    multas_de,
    suspender_a_mano,
    suspendidos_en,
)

_PARTIDO = Partido.objects.select_related(
    "categoria__torneo", "local__club", "visitante__club", "cancha", "mejor_jugador__persona"
)
TIPOS = {"gol": "Gol", "gol_en_contra": "Gol en contra", "amarilla": "Amarilla", "roja": "Roja"}


def _plantel(equipo: Equipo | None) -> list[Jugador]:
    if equipo is None:
        return []
    return list(equipo.jugadores.select_related("persona").order_by("dorsal", "persona__apellidos"))


@requiere("torneo.cargar_resultados", "cargar los partidos")
def ficha(request: HttpRequest, pk: int) -> HttpResponse:
    partido = get_object_or_404(_PARTIDO, pk=pk)
    resultado = servicio.resultado_de(partido)
    eventos = list(
        partido.eventos.select_related("equipo", "jugador__persona", "creado_por").order_by(
            "-creado_en", "-pk"
        )
    )
    equipos: list[dict[str, Any]] = [
        {"equipo": e, "escudo": escudo(e), "plantel": _plantel(e)}
        for e in (partido.local, partido.visitante)
        if e is not None
    ]
    contexto = {
        "partido": partido,
        "resultado": resultado,
        "equipos": equipos,
        "eventos": [
            {
                "tipo": TIPOS[e.tipo],
                "clase": e.tipo,
                "equipo": e.equipo.nombre,
                "jugador": e.jugador,
                "hora": timezone.localtime(e.creado_en).strftime("%H:%M"),
                "quien": e.creado_por.username if e.creado_por else "",
            }
            for e in eventos
        ],
        "eliminacion": partido.fase == Partido.Fase.ELIMINACION,
        "suspendidos": suspendidos_en(partido),
        "multas": multas_de(partido),
        "monto_multa": Reglas.model_validate(partido.categoria.torneo.reglas).multa_doble_amarilla,
        "hora": timezone.localtime(partido.inicio).strftime("%H:%M") if partido.inicio else "",
    }
    return render(request, "partidos/ficha.html", contexto)


@require_POST
@requiere("torneo.cargar_resultados", "cargar los partidos")
def accion(request: HttpRequest, pk: int) -> HttpResponse:
    partido = get_object_or_404(_PARTIDO, pk=pk)
    datos: dict[str, str] = {clave: request.POST.get(clave, "") for clave in request.POST}
    if "evento" in datos:  # un botón de la lista de jugadores: "tipo|equipo|jugador"
        partes = [*datos["evento"].split("|"), "", ""]
        datos["accion"], datos["equipo"], datos["jugador"] = partes[:3]
    try:
        _hacer(request, partido, datos)
    except NoSePuede as error:
        messages.error(request, str(error))
    return redirect("ficha-partido", pk=partido.pk)


def _equipo(partido: Partido, pk: str) -> Equipo:
    for equipo in (partido.local, partido.visitante):
        if equipo is not None and str(equipo.pk) == pk:
            return equipo
    raise NoSePuede("Elige el equipo.")


def _jugador(pk: str) -> Jugador | None:
    return Jugador.objects.filter(pk=pk).first() if pk.isdigit() else None


def _jugador_del_partido(partido: Partido, pk: str) -> Jugador:
    jugador = _jugador(pk)
    if jugador is None or jugador.equipo_id not in (partido.local_id, partido.visitante_id):
        raise NoSePuede("Elige un jugador de este partido.")
    return jugador


def _numero(texto: str) -> int:
    try:
        return max(0, int(texto))
    except ValueError:
        raise NoSePuede("Los penales son números.") from None


def _hacer(request: HttpRequest, partido: Partido, datos: dict[str, str]) -> None:
    que = datos.get("accion", "")
    match que:
        case "empezar":
            servicio.empezar(partido, request.user)
        case "gol" | "gol_en_contra" | "amarilla" | "roja":
            equipo = _equipo(partido, datos.get("equipo", ""))
            servicio.anotar(partido, que, equipo, _jugador(datos.get("jugador", "")), request.user)
        case "deshacer":
            if servicio.deshacer(partido) is None:
                raise NoSePuede("No hay nada para deshacer.")
            messages.success(request, "Se deshizo el último")
        case "wo":
            match datos.get("no_se_presento"):
                case "local":
                    servicio.wo(partido, "local", request.user)
                case "visitante":
                    servicio.wo(partido, "visitante", request.user)
                case _:
                    raise NoSePuede("Elige quién no se presentó.")
        case "penales":
            local, visitante = _numero(datos.get("local", "")), _numero(datos.get("visitante", ""))
            servicio.penales(partido, local, visitante)
        case "mejor":
            servicio.mejor_jugador(partido, _jugador(datos.get("jugador", "")))
        case "multa":
            jugador = _jugador_del_partido(partido, datos.get("jugador", ""))
            marcar_multa(partido, jugador, pagada=bool(datos.get("pagada")), usuario=request.user)
        case "suspender":
            if not request.user.has_perm("torneo.configurar_torneo"):
                raise NoSePuede("Solo la organización suspende a un jugador a mano.")
            jugador = _jugador_del_partido(partido, datos.get("jugador", ""))
            cuantos = _numero(datos.get("partidos", "1")) or 1
            suspender_a_mano(
                partido,
                jugador,
                partidos=cuantos,
                motivo=datos.get("motivo", ""),
                usuario=request.user,
            )
            messages.success(request, f"{jugador.persona} suspendido")
        case "terminar":
            servicio.terminar(partido, request.user)
            messages.success(request, "Partido terminado")
        case _:
            raise NoSePuede("Acción desconocida.")
