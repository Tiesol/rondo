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
from torneo.presentacion import escudo, url_de_imagen
from torneo.servicios import partido as servicio
from torneo.servicios import planilla
from torneo.servicios.historial import historial
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
TIPOS = {
    "gol": "Gol",
    "gol_en_contra": "Gol en contra",
    "amarilla": "Amarilla",
    "roja": "Roja",
    "amonestacion": "Amonestación",
}


def _tiempo(partido: Partido) -> str:
    """T10.9: "1.er tiempo · 12'": el tiempo que marcó la mesa y los minutos desde que empezó."""
    desde = {
        Partido.Tiempo.PRIMER_TIEMPO: partido.inicio_real,
        Partido.Tiempo.DESCANSO: partido.fin_primer_tiempo,
        Partido.Tiempo.SEGUNDO_TIEMPO: partido.fin_descanso,
    }.get(partido.tiempo)  # type: ignore[call-overload]
    if not partido.tiempo:
        return ""
    texto = partido.get_tiempo_display()
    if desde is not None:
        texto += f" · {int((timezone.now() - desde).total_seconds() // 60)}'"
    return texto


def _notas(partido: Partido, eventos: list[Any], reglas: Reglas) -> dict[int, str]:
    """Debajo de cada evento: la segunda amarilla de un jugador, hasta Sub 9, lo saca 5 min."""
    if partido.categoria.edad >= reglas.doble_amarilla_desde:
        return {}
    notas: dict[int, str] = {}
    cuenta: dict[Any, int] = {}
    for e in sorted(eventos, key=lambda e: (e.creado_en, e.pk)):
        if e.tipo == "amarilla" and e.jugador_id:
            cuenta[e.jugador_id] = cuenta.get(e.jugador_id, 0) + 1
            if cuenta[e.jugador_id] == 2:
                notas[e.pk] = "Segunda amarilla: sale 5 minutos."
    return notas


def _plantel(equipo: Equipo, dorsales: dict[int, int | None]) -> list[Jugador]:
    """El plantel, con `numero`: el dorsal de este partido si juega; si no, el habitual."""
    jugadores = list(
        equipo.jugadores.select_related("persona").order_by("dorsal", "persona__apellidos")
    )
    for jugador in jugadores:
        jugador.numero = dorsales.get(jugador.pk, jugador.dorsal)  # type: ignore[attr-defined]
        jugador.juega = jugador.pk in dorsales  # type: ignore[attr-defined]
    jugadores.sort(key=lambda j: (not j.juega, j.numero or 100))  # type: ignore[attr-defined]
    return jugadores


def _lado(partido: Partido, equipo: Equipo, dorsales: dict[int, int | None]) -> dict[str, Any]:
    plantel = _plantel(equipo, dorsales)
    suspendidos = {j.pk: motivo for j, motivo in suspendidos_en(partido)}
    lado = "local" if equipo.pk == partido.local_id else "visitante"
    return {
        "equipo": equipo,
        "escudo": escudo(equipo),
        "plantel": plantel,
        "juegan": [j for j in plantel if j.juega],  # type: ignore[attr-defined]
        "resto": [j for j in plantel if not j.juega],  # type: ignore[attr-defined]
        "entrenador": getattr(partido, f"entrenador_{lado}"),
        "filas": [
            {
                "jugador": j,
                "juega": j.juega,  # type: ignore[attr-defined]
                "dorsal": j.numero if j.juega else planilla.dorsal_sugerido(partido, j),  # type: ignore[attr-defined]
                "suspendido": suspendidos.get(j.pk, ""),
                "foto": url_de_imagen("foto", j.persona_id, j.persona.foto.name),
            }
            for j in plantel
        ],
    }


def _contexto(partido: Partido) -> dict[str, Any]:
    resultado = servicio.resultado_de(partido)
    dorsales = planilla.dorsales_del_partido(partido)
    eventos = list(
        partido.eventos.select_related("equipo", "jugador__persona", "creado_por").order_by(
            "-creado_en", "-pk"
        )
    )
    equipos: list[dict[str, Any]] = [
        _lado(partido, e, dorsales) for e in (partido.local, partido.visitante) if e is not None
    ]
    reglas = Reglas.model_validate(partido.categoria.torneo.reglas)
    notas = _notas(partido, eventos, reglas)
    return {
        "partido": partido,
        "tiempo": _tiempo(partido),
        "con_mejor_jugador": reglas.mejor_jugador,
        "resultado": resultado,
        "equipos": equipos,
        "eventos": [
            {
                "tipo": TIPOS[e.tipo],
                "clase": e.tipo,
                "equipo": e.equipo.nombre,
                "jugador": e.jugador,
                "dorsal": dorsales.get(e.jugador_id, None) if e.jugador_id else None,
                "hora": timezone.localtime(e.creado_en).strftime("%H:%M"),
                "quien": e.creado_por.username if e.creado_por else "",
                "nota": notas.get(e.pk, ""),
            }
            for e in eventos
        ],
        "eliminacion": partido.fase == Partido.Fase.ELIMINACION,
        "suspendidos": suspendidos_en(partido),
        "multas": multas_de(partido),
        "monto_multa": Reglas.model_validate(partido.categoria.torneo.reglas).multa_doble_amarilla,
        "hora": timezone.localtime(partido.inicio).strftime("%H:%M") if partido.inicio else "",
        "historial": historial(partido=partido),
    }


@requiere("torneo.cargar_resultados", "cargar los partidos")
def ficha(request: HttpRequest, pk: int) -> HttpResponse:
    partido = get_object_or_404(_PARTIDO, pk=pk)
    return render(request, "partidos/ficha.html", _contexto(partido))


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
    except (NoSePuede, planilla.NoSePuede) as error:
        messages.error(request, str(error))
    except planilla.PideConfirmar as error:
        # Se vuelve a mostrar la ficha con lo que se mandó y "Guardar igual".
        contexto = _contexto(partido)
        contexto["confirmar"] = {
            "mensaje": str(error),
            "datos": [
                (clave, valor)
                for clave, valores in request.POST.lists()
                for valor in valores
                if clave != "csrfmiddlewaretoken"
            ],
        }
        return render(request, "partidos/ficha.html", contexto)
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


def _dorsal(texto: str) -> int | None:
    texto = texto.strip()
    if not texto:
        return None
    if not texto.isdigit():
        raise NoSePuede("El dorsal es un número del 1 al 99.")
    return int(texto)


def _hacer(request: HttpRequest, partido: Partido, datos: dict[str, str]) -> None:
    que = datos.get("accion", "")
    match que:
        case "empezar":
            servicio.empezar(partido, request.user)
        case "avanzar_tiempo":
            servicio.avanzar_tiempo(partido, request.user)
        case "gol" | "gol_en_contra" | "amarilla" | "roja" | "amonestacion":
            equipo = _equipo(partido, datos.get("equipo", ""))
            servicio.anotar(partido, que, equipo, _jugador(datos.get("jugador", "")), request.user)
        case "deshacer":
            if servicio.deshacer(partido, request.user) is None:
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
            servicio.penales(partido, local, visitante, request.user)
        case "dorsal":
            jugador = _jugador_del_partido(partido, datos.get("jugador", ""))
            texto = datos.get("dorsal", "").strip()
            planilla.cambiar_dorsal(
                partido, jugador, _numero(texto) if texto else None, request.user
            )
        case "planilla":
            equipo = _equipo(partido, datos.get("equipo", ""))
            if datos.get("todos"):
                juegan = planilla.todos(partido, equipo)
            else:
                juegan = {
                    j.pk: _dorsal(datos.get(f"dorsal_{j.pk}", ""))
                    for j in equipo.jugadores.all()
                    if datos.get(f"juega_{j.pk}")
                }
            planilla.guardar_planilla(
                partido,
                equipo,
                juegan,
                request.user,
                confirmado=datos.get("confirmar") == "1",
                entrenador=bool(datos.get("entrenador")) if not datos.get("todos") else None,
            )
            messages.success(request, f"Planilla de {equipo.nombre} guardada")
        case "mejor":
            servicio.mejor_jugador(partido, _jugador(datos.get("jugador", "")), request.user)
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
