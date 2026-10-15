"""Propuestas de reprogramación (T5.3): verlas y aplicar una."""

from datetime import datetime, timedelta
from typing import Any

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from dominio.partido import Lado
from dominio.programador.relajar import Relajar
from torneo.forms.bloqueo import FormularioReprogramar
from torneo.forms.reprogramar import CamposAflojar
from torneo.models import Bloqueo, Corrida, Franja, Partido
from torneo.permisos import requiere
from torneo.presentacion import cruce, lugar
from torneo.servicios.partido import NoSePuede, wo
from torneo.servicios.reprogramar import (
    NoSePuedeAplicar,
    afectados_por,
    aplicar,
    calcular_propuestas,
    calcular_propuestas_en,
    veces_que_reprogramo,
)
from torneo.views.confirmar import confirmado, pedir_confirmacion


def _lugar(guardado: list[str] | None) -> str:
    if guardado is None:
        return "Sin programar"
    codigo, cuando = guardado
    return lugar(timezone.make_aware(datetime.fromisoformat(cuando)), codigo)


def _titulo(propuesta: list[dict[str, Any]]) -> str:
    """ "Mover 2 partidos", "Ubicar 3 partidos" o "Ubicar 3 y mover 1"."""
    ubicar = sum(1 for m in propuesta if m["antes"] is None)
    mover = len(propuesta) - ubicar

    def partidos(n: int) -> str:
        return f"{n} partido{'s' if n != 1 else ''}"

    if ubicar and mover:
        return f"Ubicar {ubicar} y mover {mover}"
    return f"Ubicar {partidos(ubicar)}" if ubicar else f"Mover {partidos(mover)}"


def _inicial_aflojar(relajar: Relajar) -> dict[str, Any]:
    return {
        "turnos_libres": relajar.turnos_libres,
        "max_por_dia": relajar.max_por_dia,
        "orden_blando": relajar.orden == "blanda",
        "minutos_extra": relajar.minutos_extra or None,
        "usar_mitades": relajar.usar_mitades,
    }


def _volver(corrida: Corrida) -> str:
    if "bloqueo" in corrida.parametros:
        return reverse("acf", args=[corrida.torneo_id])
    if dia := corrida.parametros.get("dia"):
        return reverse("calendario-dia", args=[dia])
    return reverse("calendario")


@require_POST
@requiere("torneo.configurar_torneo", "reprogramar")
def propuestas(request: HttpRequest, pk: int) -> HttpResponse:
    bloqueo = get_object_or_404(Bloqueo.objects.select_related("torneo"), pk=pk)
    aflojar = CamposAflojar(request.POST)
    relajar = aflojar.relajar() if aflojar.is_valid() else None
    corrida = calcular_propuestas(bloqueo, request.user, relajar=relajar)
    return redirect("ver-propuestas", pk=corrida.pk)


@require_POST
@requiere("torneo.configurar_torneo", "reprogramar")
def recalcular(request: HttpRequest, pk: int) -> HttpResponse:
    """B6: las mismas propuestas, aflojando reglas solo esta vez. Queda anotado en la corrida."""
    anterior = get_object_or_404(Corrida, pk=pk, tipo=Corrida.Tipo.REPROGRAMAR)
    aflojar = CamposAflojar(request.POST)
    if not aflojar.is_valid():
        messages.error(request, "Revisa los números de las reglas.")
        return redirect("ver-propuestas", pk=anterior.pk)
    parametros = anterior.parametros
    desde = datetime.fromisoformat(parametros["desde"])
    hasta = datetime.fromisoformat(parametros["hasta"])
    franja = Franja.objects.filter(pk=parametros.get("franja_extra")).first()
    origen = {
        k: v for k, v in parametros.items() if k in ("bloqueo", "dia", "franja_extra", "categoria")
    }
    corrida = calcular_propuestas_en(
        anterior.torneo,
        desde,
        hasta,
        motivo=parametros.get("motivo", ""),
        origen=origen,
        usuario=request.user,
        preferidas=[franja] if franja else None,
        relajar=aflojar.relajar(),
    )
    return redirect("ver-propuestas", pk=corrida.pk)


@requiere("torneo.configurar_torneo", "reprogramar")
def ver_propuestas(request: HttpRequest, pk: int) -> HttpResponse:
    corrida = get_object_or_404(Corrida, pk=pk, tipo=Corrida.Tipo.REPROGRAMAR)
    guardadas = corrida.resultado.get("propuestas", [])
    ids = {m["partido"] for propuesta in guardadas for m in propuesta}
    partidos = {
        p.pk: p
        for p in Partido.objects.filter(pk__in=ids).select_related(
            "local", "visitante", "categoria"
        )
    }
    vista: list[dict[str, Any]] = []
    for indice, propuesta in enumerate(guardadas):
        vista.append(
            {
                "indice": indice,
                "publicados": sum(1 for m in propuesta if m["antes"] is not None),
                "titulo": _titulo(propuesta),
                "movimientos": [
                    {
                        "antes": _lugar(m["antes"]),
                        "despues": _lugar(m["despues"]),
                        "cruce": cruce(partidos[m["partido"]]),
                        "categoria": str(partidos[m["partido"]].categoria),
                        "motivo": m.get("motivo", ""),  # T13.18
                    }
                    for m in propuesta
                    if m["partido"] in partidos
                ],
            }
        )
    pedido = Bloqueo.objects.filter(pk=corrida.parametros.get("bloqueo")).first()
    afectados = afectados_por(pedido) if pedido else []
    veces = {e.pk: veces_que_reprogramo(e) for e in (pedido.equipos.all() if pedido else [])}
    relajar = Relajar.desde_dict(corrida.parametros.get("relajar") or {})
    return render(
        request,
        "reprogramar/propuestas.html",
        {
            "corrida": corrida,
            "propuestas": vista,
            "motivo": corrida.parametros.get("motivo", ""),
            "aflojadas": relajar.describir(),
            "form": CamposAflojar(initial=_inicial_aflojar(relajar)),
            "volver": _volver(corrida),
            # T10.10: dar W.O. en lugar de reprogramar, y cuántas veces ya reprogramó.
            "afectados": [
                {
                    "partido": p,
                    "equipo": e,
                    "cruce": cruce(p),
                    "aviso": _ya_reprogramo(e.nombre, veces.get(e.pk, 0)),
                }
                for p, e in afectados
            ],
        },
    )


def _ya_reprogramo(nombre: str, veces: int) -> str:
    """ "River ya reprogramó 2 veces": sin límite, la organización decide (T10.10)."""
    if not veces:
        return ""
    return f"{nombre} ya reprogramó {veces} {'vez' if veces == 1 else 'veces'}."


@require_POST
@requiere("torneo.configurar_torneo", "reprogramar")
def dar_wo(request: HttpRequest, pk: int) -> HttpResponse:
    """T10.10: el equipo que pidió reprogramar pierde el partido por W.O."""
    corrida = get_object_or_404(Corrida, pk=pk, tipo=Corrida.Tipo.REPROGRAMAR)
    pedido = get_object_or_404(Bloqueo, pk=corrida.parametros.get("bloqueo"))
    elegido = next(
        (
            (p, e)
            for p, e in afectados_por(pedido)
            if str(p.pk) == request.POST.get("partido") and str(e.pk) == request.POST.get("equipo")
        ),
        None,
    )
    if elegido is None:
        messages.error(request, "Ese partido no es del pedido.")
        return redirect("ver-propuestas", pk=corrida.pk)
    partido, equipo = elegido
    lado: Lado = "local" if partido.local_id == equipo.pk else "visitante"
    if not confirmado(request):
        return pedir_confirmacion(
            request,
            mensaje=f"{equipo.nombre} pierde {cruce(partido)} por W.O. (marcador del reglamento).",
            boton="Dar el W.O.",
            volver=reverse("ver-propuestas", args=[corrida.pk]),
            peligro=True,
        )
    try:
        wo(partido, lado, request.user)
    except NoSePuede as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"W.O.: {equipo.nombre} pierde {cruce(partido)}")
    return redirect("ver-propuestas", pk=corrida.pk)


@require_POST
@requiere("torneo.configurar_torneo", "reprogramar")
def aplicar_propuesta(request: HttpRequest, pk: int, indice: int) -> HttpResponse:
    corrida = get_object_or_404(Corrida, pk=pk, tipo=Corrida.Tipo.REPROGRAMAR)
    if not 0 <= indice < len(corrida.resultado.get("propuestas", [])):
        raise Http404
    if not confirmado(request):
        movimientos = corrida.resultado["propuestas"][indice]
        publicados = sum(1 for m in movimientos if m["antes"] is not None)
        nuevos = len(movimientos) - publicados
        partes = []
        if nuevos:
            partes.append(f"se ubican {nuevos} partido{'s' if nuevos != 1 else ''}")
        if publicados:
            partes.append(
                f"se mueven {publicados} que ya estaban publicados"
                if publicados != 1
                else "se mueve 1 que ya estaba publicado"
            )
        return pedir_confirmacion(
            request,
            mensaje="Al aplicar esta propuesta " + " y ".join(partes) + ".",
            boton="Aplicar",
            volver=reverse("ver-propuestas", args=[corrida.pk]),
        )
    try:
        cambios = aplicar(corrida, indice, request.user)
    except NoSePuedeAplicar as error:
        messages.error(request, str(error))
        return redirect("ver-propuestas", pk=corrida.pk)
    messages.success(request, f"Propuesta aplicada: {len(cambios)} partido(s) movido(s)")
    primero = min((c.inicio_despues for c in cambios if c.inicio_despues), default=None)
    if primero:
        return redirect("calendario-dia", fecha=timezone.localtime(primero).date().isoformat())
    return redirect("calendario")


@requiere("torneo.configurar_torneo", "reprogramar")
def reprogramar_partido(request: HttpRequest, pk: int) -> HttpResponse:
    """T13.15: desde la ficha o el calendario. Si un equipo no puede en ese horario, queda un
    bloqueo (con su motivo) y se calculan las propuestas; también se puede mover a mano o
    intercambiar."""
    partido = get_object_or_404(
        Partido.objects.select_related("categoria__torneo", "cancha", "local", "visitante"), pk=pk
    )
    formulario = FormularioReprogramar(request.POST or None, partido=partido)
    if request.method == "POST" and partido.inicio is not None and formulario.is_valid():
        bloqueo = Bloqueo.objects.create(
            torneo=partido.categoria.torneo,
            inicio=partido.inicio,
            fin=partido.inicio + timedelta(minutes=partido.categoria.minutos_partido),
            motivo=formulario.cleaned_data["motivo"],
        )
        bloqueo.equipos.set(formulario.cleaned_data["equipos"])
        corrida = calcular_propuestas(bloqueo, request.user)
        return redirect("ver-propuestas", pk=corrida.pk)
    return render(
        request,
        "reprogramar/partido.html",
        {
            "partido": partido,
            "cruce": cruce(partido),
            "ahora": lugar(partido.inicio, partido.cancha.codigo if partido.cancha else ""),
            "form": formulario,
        },
    )
