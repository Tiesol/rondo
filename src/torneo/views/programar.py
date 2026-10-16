"""Programar (T3.7 y T4.6): "¿Entra todo?", el botón de programar y su resultado."""

from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from dominio.capacidad import GrupoDeCanchas
from torneo.models import Corrida, Partido, Torneo
from torneo.permisos import requiere
from torneo.presentacion import DIAS_CORTOS
from torneo.servicios.capacidad import capacidad_del_torneo
from torneo.servicios.programador import (
    CON_SOLUCION,
    ProgramacionEnCurso,
    Resumen,
    huella,
    programar_torneo,
    resumen_antes_de_programar,
)
from torneo.views.calendario import dias_de_fin_de_semana
from torneo.views.confirmar import confirmado, pedir_confirmacion
from torneo.views.fragmentos import pide_fragmento


def _horas(minutos: int) -> str:
    horas = minutos / 60
    if horas >= 10 or horas == int(horas):
        return f"{horas:.0f}"
    return f"{horas:.1f}".replace(".", ",")


def _fila(grupo: GrupoDeCanchas, con_extra: GrupoDeCanchas | None = None) -> dict[str, Any]:
    return {
        "entra_con_extra": con_extra is not None and not grupo.entra and con_extra.entra,
        "titulo": " y ".join(grupo.canchas) or "Sin canchas compatibles",
        "categorias": list(grupo.categorias),
        "pedido": _horas(grupo.pedido),
        "disponible": _horas(grupo.disponible),
        "faltan": _horas(grupo.faltan),
        "entra": grupo.entra,
        "uso": min(round(100 * grupo.pedido / grupo.disponible), 100) if grupo.disponible else 100,
    }


def en_palabras(grupo: GrupoDeCanchas, *, partidos: int, turno: int) -> str:
    """T13.31: "C3: 14 partidos (16 h) de 88 h disponibles. Entran unos 60 partidos más de 70
    min." `turno` es el más largo de las categorías del grupo."""
    canchas = " y ".join(grupo.canchas) or "Sin canchas compatibles"
    texto = (
        f"{canchas}: {partidos} partido{'s' if partidos != 1 else ''} "
        f"({_horas(grupo.pedido)} h) de {_horas(grupo.disponible)} h disponibles."
    )
    if grupo.entra and turno:
        # T13.34: el flujo nunca ubica más de lo pedido; lo que entra sale de lo libre.
        mas = (grupo.disponible - grupo.pedido) // turno
        texto += f" Entran unos {mas} partidos más de {turno} min."
    return texto


def una_linea(grupo: GrupoDeCanchas, *, partidos: int, turno: int, con_extra: bool = False) -> str:
    """T13.37: la capacidad de un grupo de canchas en una línea; las canchas y las horas ya
    están en el título y el chip. "130 partidos · entran unos 90 más de 50 min"; si no
    entra, lo que falta va primero: "Faltan 6 h · 93 partidos"."""
    texto = f"{partidos} partido{'s' if partidos != 1 else ''}"
    if con_extra:
        return f"Entra usando el tiempo agregado · {texto}"
    if not grupo.entra:
        return f"Faltan {_horas(grupo.faltan)} h · {texto}"
    if turno:
        return (
            f"{texto} · entran unos {(grupo.disponible - grupo.pedido) // turno} más de {turno} min"
        )
    return texto


def minutos_por_dia(faltan: int, dias: int) -> int:
    """Lo que falta repartido en esos días, redondeado hacia arriba a la media hora."""
    por_dia = -(-faltan // dias)
    return -(-por_dia // 30) * 30


def sugerencia_para_que_entre(grupo: GrupoDeCanchas, *, dias_de_fin_de_semana: int) -> str:
    """T13.8 (P79): lo que falta, repartido en los sábados y domingos (antes o después del
    horario), solo para esas canchas. Los jueves quedan para las suspensiones."""
    if grupo.entra or not dias_de_fin_de_semana:
        return ""
    por_dia = minutos_por_dia(grupo.faltan, dias_de_fin_de_semana)
    canchas = " y ".join(grupo.canchas)
    return (
        f"Para que entre: unas {_horas(por_dia)} h por día en los {dias_de_fin_de_semana} "
        f"sábados y domingos, solo para {canchas}, antes o después del horario. Se agrega en "
        "Calendario → «Agregar tiempo» → «Repetir en todos los sábados y domingos»."
    )


def _plural(n: int, uno: str, varios: str) -> str:
    return f"{n} {uno if n == 1 else varios}"


def _que_pasa(resumen: Resumen) -> str:
    mueve = _plural(resumen.futuros, "partido ya programado", "partidos ya programados")
    return f"Volver a programar mueve {mueve} y ubica los que faltan. Nada se ubica antes de ahora."


def _detalle(resumen: Resumen) -> list[str]:
    lineas = []
    if resumen.jugados:
        jugados = _plural(resumen.jugados, "jugado o en juego", "jugados o en juego")
        lineas.append(f"No se mueven: {jugados}.")
    if resumen.sin_resultado:
        pasados = _plural(
            len(resumen.sin_resultado), "partido cuya hora ya pasó", "partidos cuya hora ya pasó"
        )
        lineas.append(f"No se mueven: {pasados}, y les falta el resultado.")
    lineas.append(f"Se mueven: {_plural(resumen.futuros, 'partido', 'partidos')} programados.")
    return lineas


def cuando(momento: datetime, *, ahora: datetime | None = None) -> str:
    """T13.36: "hoy 19:20", "ayer 19:20" o "mié 21/10 19:20", en hora de Bolivia."""
    local = timezone.localtime(momento)
    hoy = timezone.localtime(ahora or timezone.now()).date()
    hora = f"{local:%H:%M}"
    if local.date() == hoy:
        return f"hoy {hora}"
    if local.date() == hoy - timedelta(days=1):
        return f"ayer {hora}"
    return f"{DIAS_CORTOS[local.weekday()].lower()} {local.day}/{local.month} {hora}"


def _ultima(torneo: Torneo) -> Corrida | None:
    return (
        Corrida.objects.filter(torneo=torneo, tipo=Corrida.Tipo.PROGRAMAR)
        .exclude(estado=Corrida.Estado.CORRIENDO)
        .first()
    )


def _resultado(torneo: Torneo) -> dict[str, Any] | None:
    """La última programación terminada, lista para mostrar: cuándo fue y si después cambió
    algo (T13.36)."""
    corrida = _ultima(torneo)
    if corrida is None:
        return None
    resultado = corrida.resultado
    if resultado.get("oculta"):
        return {"oculta": True}
    datos = _datos_de_la_corrida(torneo, corrida)
    datos["cuando"] = cuando(corrida.inicio)
    guardada = resultado.get("huella")
    datos["desactualizada"] = bool(guardada) and guardada != huella(torneo)
    return datos


def _datos_de_la_corrida(torneo: Torneo, corrida: Corrida) -> dict[str, Any]:
    if corrida.estado == Corrida.Estado.FALLIDA:
        return {"fallida": True, "corrida": corrida}
    resultado = corrida.resultado
    total, ubicados = resultado.get("total", 0), resultado.get("ubicados", 0)
    # T13.35: sin ningún calendario en el tiempo. Las corridas de antes no tienen la marca:
    # 0 ubicados y el solver sin solución. Con solución y 0 ubicados, es que nada entra.
    vieja_sin_solucion = (
        "sin_solucion" not in resultado
        and total
        and not ubicados
        and resultado.get("estado_solver") not in CON_SOLUCION
    )
    if resultado.get("sin_solucion") or vieja_sin_solucion:
        return {"sin_solucion": True, "corrida": corrida, "total": total}
    # T11.2: los que se ubicaron a mano después ya no figuran.
    pendientes = set(
        Partido.objects.filter(
            categoria__torneo=torneo, estado=Partido.Estado.PENDIENTE
        ).values_list("pk", flat=True)
    )
    return {
        "corrida": corrida,
        "ubicados": ubicados,
        "total": total,
        "choques": sum(resultado.get("choques", {}).values()),
        "sin_ubicar": [s for s in resultado.get("sin_ubicar", []) if s["id"] in pendientes],
        "sin_resultado": resultado.get("sin_resultado", []),
    }


@require_POST
@requiere("torneo.configurar_torneo", "programar")
def ocultar(request: HttpRequest, pk: int) -> HttpResponse:
    """T13.36: esconde el resultado de la última programación hasta la próxima."""
    torneo = get_object_or_404(Torneo, pk=pk)
    corrida = _ultima(torneo)
    if corrida is not None:
        corrida.resultado = {**corrida.resultado, "oculta": True}
        corrida.save(update_fields=["resultado"])
    if pide_fragmento(request):
        return render(
            request, "torneo/_resultado_programacion.html", {"resultado": None, "torneo": torneo}
        )
    return redirect("programar", pk=torneo.pk)


@requiere("torneo.configurar_torneo", "programar")
def programar(request: HttpRequest, pk: int) -> HttpResponse:
    torneo = get_object_or_404(Torneo, pk=pk)
    resumen = resumen_antes_de_programar(torneo)
    if request.method == "POST":
        faltan = request.POST.get("modo") == "faltan"
        if not faltan and resumen.hay_publicados and not confirmado(request):
            return pedir_confirmacion(
                request,
                mensaje=_que_pasa(resumen),
                detalle=_detalle(resumen),
                boton="Volver a programar",
                volver=reverse("programar", args=[torneo.pk]),
                peligro=True,
                destino="resultado-programacion",
            )
        try:
            programar_torneo(torneo, request.user, solo_lo_que_falta=faltan)
        except ProgramacionEnCurso as error:
            messages.error(request, str(error))
        if pide_fragmento(request):
            return render(
                request,
                "torneo/_resultado_programacion.html",
                {"resultado": _resultado(torneo), "torneo": torneo},
            )
        return redirect("programar", pk=torneo.pk)

    capacidad = capacidad_del_torneo(torneo)
    # T11.4: la eliminación ya no tiene un fin de semana propio; se mide todo el torneo.
    con_extra = {g.canchas: g for g in capacidad.con_extra}
    filas = [_fila(g, con_extra.get(g.canchas)) for g in capacidad.total]
    dias = len(dias_de_fin_de_semana(torneo))
    for fila, grupo in zip(filas, capacidad.total, strict=True):
        de_las_categorias = [capacidad.partidos.get(c, (0, 0)) for c in grupo.categorias]
        partidos = sum(n for n, _ in de_las_categorias)
        turno = max((t for _, t in de_las_categorias), default=0)
        fila["en_palabras"] = en_palabras(grupo, partidos=partidos, turno=turno)
        fila["una_linea"] = una_linea(
            grupo, partidos=partidos, turno=turno, con_extra=fila["entra_con_extra"]
        )
        if not fila["entra_con_extra"]:
            fila["sugerencia"] = sugerencia_para_que_entre(
                con_extra.get(grupo.canchas, grupo), dias_de_fin_de_semana=dias
            )
    return render(
        request,
        "torneo/programar.html",
        {
            "torneo": torneo,
            "resumen": resumen,
            "filas": filas,
            "minutos_maximos": max(1, -(-settings.PROGRAMADOR_SEGUNDOS // 60)),
            "no_entra": any(not f["entra"] and not f["entra_con_extra"] for f in filas),
            "capacidad": capacidad,
            "estimadas": ", ".join(capacidad.estimadas),
            "sin_formato": ", ".join(capacidad.sin_formato),
            "resultado": _resultado(torneo),
        },
    )
