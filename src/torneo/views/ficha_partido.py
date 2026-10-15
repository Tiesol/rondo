"""La ficha del partido para la mesa (T8.6, B3): se carga desde el celular durante el partido.

Botones grandes "Gol", "Amarilla" y "Roja": cada uno abre la lista del equipo, con dorsal y
nombre. Cada acción es un POST que vuelve a la ficha (funciona sin JavaScript). Muestra
nombres de jugadores: solo para quien carga resultados (organización y mesa, P64).
"""

from collections import Counter
from datetime import datetime, time, timedelta
from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from dominio.config import Reglas
from torneo.models import Equipo, Evento, Jugador, Partido
from torneo.permisos import requiere
from torneo.presentacion import cruce, escudo, url_de_imagen
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
from torneo.views.confirmar import confirmado, pedir_confirmacion

_PARTIDO = Partido.objects.select_related(
    "categoria__torneo", "local__club", "visitante__club", "cancha", "mejor_jugador__persona"
)
TIPOS = {
    "gol": "Gol",
    "gol_en_contra": "Gol en contra",
    "amarilla": "Amarilla",
    "roja": "Roja",
    "amonestacion": "Amonestación",
    "lesion": "Lesión",
}


def _tiempo(partido: Partido) -> str:
    """T10.9 y T11.10: "2.º tiempo · 27'": el tiempo que marcó la mesa y el minuto en curso."""
    if not partido.tiempo:
        return ""
    texto = partido.get_tiempo_display()
    if partido.tiempo != Partido.Tiempo.DESCANSO and (minuto := servicio.minuto_actual(partido)):
        texto += f" · {minuto}'"
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
                vuelve = timezone.localtime(e.creado_en + timedelta(minutes=5))
                notas[e.pk] = f"Afuera 5 min · vuelve {vuelve:%H:%M}"
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


def _lado(
    partido: Partido,
    equipo: Equipo,
    dorsales: dict[int, int | None],
    verificados: set[int],
    abierto: bool = False,
) -> dict[str, Any]:
    plantel = _plantel(equipo, dorsales)
    suspendidos = {j.pk: motivo for j, motivo in suspendidos_en(partido)}
    lado = "local" if equipo.pk == partido.local_id else "visitante"
    juegan = [j for j in plantel if j.juega]  # type: ignore[attr-defined]
    # C1: los dorsales repetidos entre los que juegan se marcan.
    veces = Counter(j.numero for j in juegan if j.numero is not None)  # type: ignore[attr-defined]
    return {
        "verificados": sum(1 for j in juegan if j.pk in verificados),
        "abierto": abierto,
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
                "repetido": j.juega and veces[j.numero] > 1,  # type: ignore[attr-defined]
                "ci": j.persona.documento or "Sin CI",
                "ci_verificado": j.pk in verificados,
                "foto": url_de_imagen("foto", j.persona_id, j.persona.foto.name),
            }
            for j in plantel
        ],
    }


def _tanda(partido: Partido, resultado: Any, equipos: list[dict[str, Any]]) -> dict[str, Any]:
    """T11.13: los penales, si es una llave empatada (o ya se empezaron a patear)."""
    tiros = list(partido.tiros.all())
    empatado = resultado.marcador[0] == resultado.marcador[1]
    if partido.fase != Partido.Fase.ELIMINACION or resultado.wo or not partido.empezado:
        return {}
    if not (empatado or tiros):
        return {}
    estado = servicio.estado_penales(partido)
    lados = []
    for lado in equipos:
        suyos = [t.convirtio for t in tiros if t.equipo_id == lado["equipo"].pk]
        lados.append({"equipo": lado["equipo"], "tiros": suyos, "goles": sum(suyos)})
    nombres = {"local": partido.local, "visitante": partido.visitante}
    return {
        "lados": lados,
        "hay_tiros": bool(tiros),
        "ganador": nombres[estado.ganador] if estado.ganador else None,
        "patea": nombres[estado.patea] if estado.patea else None,
        "muerte_subita": estado.muerte_subita,
        "por_equipo": Reglas.model_validate(partido.categoria.torneo.reglas).penales_por_equipo,
    }


# B7: las acciones importantes piden "¿Estás seguro?" y dicen qué va a pasar.
CONFIRMAN = {
    "terminar": "Terminar el partido",
    "wo": "Dar el W.O.",
    "quitar_wo": "Quitar el W.O.",
    "borrar": "Borrar",
    "reprogramar_en_juego": "Reprogramar",
}


def _que_pasa(partido: Partido, datos: dict[str, str]) -> str:
    equipos = cruce(partido)
    match datos.get("accion"):
        case "terminar":
            local, visitante = servicio.resultado_de(partido).marcador
            return f"Se termina {equipos} con el marcador {local} a {visitante}."
        case "wo":
            ausente = partido.local if datos.get("no_se_presento") == "local" else partido.visitante
            return f"No se presentó {ausente.nombre if ausente else 'el equipo'}: pierde por W.O."
        case "quitar_wo":
            return f"Se quita el W.O. de {equipos}: el partido vuelve a estar por jugar."
        case "borrar":
            evento = partido.eventos.filter(pk=datos.get("evento_id") or 0).first()
            que = evento.get_tipo_display() if evento else "el evento"
            return f"Se borra «{que}» de {equipos}. Queda en el historial."
        case "reprogramar_en_juego":
            n = partido.eventos.count()
            return (
                f"{equipos} vuelve a «sin programar». Se borran sus {n} eventos (goles y "
                "tarjetas); quedan en el historial."
            )
    return ""


def _dia_suspendido(partido: Partido) -> bool:
    """B3: el día del partido se suspendió (todas sus franjas)."""
    if partido.inicio is None:
        return False
    dia = timezone.localtime(partido.inicio).date()
    franjas = [
        f
        for f in partido.categoria.torneo.franjas.all()
        if timezone.localtime(f.inicio).date() == dia
    ]
    return bool(franjas) and all(f.suspendida for f in franjas)


def _contexto(partido: Partido, abrir: int | None = None) -> dict[str, Any]:
    resultado = servicio.resultado_de(partido)
    dorsales = planilla.dorsales_del_partido(partido)
    eventos = list(
        partido.eventos.select_related("equipo", "jugador__persona", "creado_por").order_by(
            "-creado_en", "-pk"
        )
    )
    equipos: list[dict[str, Any]] = [
        _lado(partido, e, dorsales, planilla.ci_verificados(partido), e.pk == abrir)
        for e in (partido.local, partido.visitante)
        if e is not None
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
                "pk": e.pk,
                "minuto": e.minuto,
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
        "tanda": _tanda(partido, resultado, equipos),
        "suspendidos": suspendidos_en(partido),
        "multas": multas_de(partido),
        "monto_multa": Reglas.model_validate(partido.categoria.torneo.reglas).multa_doble_amarilla,
        "hora": timezone.localtime(partido.inicio).strftime("%H:%M") if partido.inicio else "",
        "historial": historial(partido=partido),
        "dia_suspendido": _dia_suspendido(partido),
        "olvidado": (
            timezone.localtime(fin).strftime("%H:%M")
            if (fin := servicio.olvidado_desde(partido))
            else ""
        ),
        "horas": [
            {
                "campo": campo,
                "texto": texto,
                "valor": (
                    timezone.localtime(getattr(partido, campo)).strftime("%H:%M")
                    if getattr(partido, campo)
                    else ""
                ),
            }
            for campo, texto in servicio.HORAS.items()
        ],
    }


@requiere("torneo.cargar_resultados", "cargar los partidos")
def ficha(request: HttpRequest, pk: int) -> HttpResponse:
    partido = get_object_or_404(_PARTIDO, pk=pk)
    if servicio.cerrar_olvidados(partido.categoria.torneo):  # T11.12
        partido.refresh_from_db()
    abrir = request.GET.get("equipo", "")
    contexto = _contexto(partido, int(abrir) if abrir.isdigit() else None)
    return render(request, "partidos/ficha.html", contexto)


@require_POST
@requiere("torneo.cargar_resultados", "cargar los partidos")
def accion(request: HttpRequest, pk: int) -> HttpResponse:
    partido = get_object_or_404(_PARTIDO, pk=pk)
    datos: dict[str, str] = {clave: request.POST.get(clave, "") for clave in request.POST}
    if "evento" in datos:  # un botón de la lista de jugadores: "tipo|equipo|jugador"
        partes = [*datos["evento"].split("|"), "", ""]
        datos["accion"], datos["equipo"], datos["jugador"] = partes[:3]
    if datos.get("accion") in CONFIRMAN and not confirmado(request):
        return pedir_confirmacion(
            request,
            mensaje=_que_pasa(partido, datos),
            boton=CONFIRMAN[datos["accion"]],
            volver=reverse("ficha-partido", args=[partido.pk]),
            peligro=True,
        )
    try:
        _hacer(request, partido, datos)
    except (NoSePuede, planilla.NoSePuede) as error:
        messages.error(request, str(error))
    except Reprogramado:
        return redirect("mover", pk=partido.pk)
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
        raise NoSePuede("Escribe un número.") from None


class Reprogramado(Exception):
    """Después de reprogramar un partido en juego, se pasa a ubicarlo."""


def _evento(partido: Partido, datos: dict[str, str]) -> Evento:
    evento = partido.eventos.filter(pk=datos.get("evento_id", "0") or 0).first()
    if evento is None:
        raise NoSePuede("Ese evento ya no está.")
    return evento


def _horas(partido: Partido, datos: dict[str, str]) -> dict[str, Any]:
    """Las horas que se mandan (HH:MM), el mismo día del partido."""
    base = partido.inicio_real or partido.inicio or timezone.now()
    dia = timezone.localtime(base).date()
    horas: dict[str, Any] = {}
    for campo in servicio.HORAS:
        if campo not in datos:
            continue
        texto = datos[campo].strip()
        if not texto:
            horas[campo] = None
            continue
        try:
            hora = time.fromisoformat(texto)
        except ValueError:
            raise NoSePuede("Las horas van como 18:05.") from None
        horas[campo] = timezone.make_aware(datetime.combine(dia, hora))
    return horas


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
        case "gol" | "gol_en_contra" | "amarilla" | "roja" | "amonestacion" | "lesion":
            equipo = _equipo(partido, datos.get("equipo", ""))
            servicio.anotar(partido, que, equipo, _jugador(datos.get("jugador", "")), request.user)
        case "minuto":
            texto = datos.get("minuto", "").strip()
            minuto = _numero(texto) if texto else None
            servicio.corregir_minuto(_evento(partido, datos), minuto, request.user)
        case "borrar":
            servicio.borrar_evento(_evento(partido, datos), request.user)
            messages.success(request, "Borrado")
        case "horas":
            servicio.corregir_horas(partido, _horas(partido, datos), request.user)
            messages.success(request, "Horas guardadas")
        case "revisado":
            servicio.marcar_revisado(partido, request.user)
        case "quitar_wo":
            servicio.quitar_wo(partido, request.user)
        case "reprogramar_en_juego":
            if not request.user.has_perm("torneo.configurar_torneo"):  # P85 (T13.5)
                raise NoSePuede("Solo la organización reprograma un partido.")
            servicio.reprogramar_en_juego(partido, request.user)
            messages.success(request, "Sin programar: ubícalo en un día y una cancha")
            raise Reprogramado
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
        case "penal":
            equipo = _equipo(partido, datos.get("equipo", ""))
            servicio.patear(partido, equipo, bool(datos.get("convirtio")), request.user)
        case "deshacer_penal":
            servicio.deshacer_penal(partido, request.user)
        case "penales":
            local, visitante = _numero(datos.get("local", "")), _numero(datos.get("visitante", ""))
            servicio.penales(partido, local, visitante, request.user)
        case "dorsal":
            jugador = _jugador_del_partido(partido, datos.get("jugador", ""))
            texto = datos.get("dorsal", "").strip()
            planilla.cambiar_dorsal(
                partido,
                jugador,
                _numero(texto) if texto else None,
                request.user,
                confirmado=datos.get("confirmar") == "1",
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
            tocan_el_ci = not datos.get("todos")
            planilla.guardar_planilla(
                partido,
                equipo,
                juegan,
                request.user,
                confirmado=datos.get("confirmar") == "1",
                entrenador=bool(datos.get("entrenador")) if not datos.get("todos") else None,
                verificados=(
                    {int(clave.removeprefix("ci_")) for clave in datos if clave.startswith("ci_")}
                    if tocan_el_ci
                    else None
                ),
                verificar_todos=bool(datos.get("verificar_todos")),
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
