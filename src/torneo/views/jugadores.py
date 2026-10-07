"""Alta de jugadores y profes con avisos en vivo, y verificación (T2.6, INS-12).

Los formularios llevan datos personales de menores: son sensibles (no van a ningún reporte
de error), y el log nunca registra cuerpos de requests.
"""

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_POST

from dominio.config import CuerpoTecnico
from dominio.inscripcion import Hallazgo
from torneo.forms.jugador import FormularioJugador, FormularioProfe, datos_a_medias
from torneo.models import Equipo, Jugador
from torneo.permisos import requiere
from torneo.servicios import inscripcion
from torneo.views.fragmentos import pide_fragmento

_EQUIPO = Equipo.objects.select_related("club", "categoria__torneo")

# Después de guardar, estos avisos ya se ven en la ficha (chips del encabezado y marcas de
# cada fila): no se repiten como avisos flotantes.
_VISIBLES_EN_LA_FICHA = {"INS-03", "INS-09", "INS-10"}


def _es_organizacion(request: HttpRequest) -> bool:
    return request.user.has_perm("torneo.configurar_torneo")


def _roles(equipo: Equipo) -> tuple[str, ...]:
    return CuerpoTecnico.model_validate(equipo.categoria.torneo.cuerpo_tecnico).roles


def _avisar(request: HttpRequest, quien: str, resultado: inscripcion.Resultado) -> HttpResponse:
    messages.success(request, f"{quien} agregado")
    for aviso in resultado.avisos:
        if aviso.regla not in _VISIBLES_EN_LA_FICHA:
            messages.warning(request, aviso.mensaje)
    assert resultado.registro is not None
    seccion = "plantel" if isinstance(resultado.registro, Jugador) else "cuerpo-tecnico"
    return redirect("equipo", pk=resultado.registro.equipo_id, seccion=seccion)


def _hallazgos(request: HttpRequest, hallazgos: list[Hallazgo]) -> HttpResponse:
    return render(request, "equipos/_hallazgos.html", {"hallazgos": hallazgos})


@sensitive_post_parameters()
@sensitive_variables()
@requiere("torneo.inscribir_equipos", "cargar listas")
def agregar_jugador(request: HttpRequest, pk: int) -> HttpResponse:
    equipo = get_object_or_404(_EQUIPO, pk=pk)
    formulario = FormularioJugador(request.POST or None)
    hallazgos: list[Hallazgo] = []
    if request.method == "POST" and formulario.is_valid():
        resultado = inscripcion.agregar_jugador(
            equipo,
            formulario.datos(),
            formulario.cleaned_data["dorsal"],
            hoy=timezone.localdate(),
            es_organizacion=_es_organizacion(request),
        )
        if resultado.guardado:
            return _avisar(request, formulario.cleaned_data["nombres"], resultado)
        hallazgos = resultado.hallazgos
    return render(
        request,
        "equipos/agregar.html",
        {"equipo": equipo, "form": formulario, "hallazgos": hallazgos, "que": "jugador"},
    )


@require_POST
@sensitive_post_parameters()
@sensitive_variables()
@requiere("torneo.inscribir_equipos", "cargar listas")
def revisar_jugador(request: HttpRequest, pk: int) -> HttpResponse:
    """Avisos en vivo, sin guardar: lo que todavía no se escribió no se reclama."""
    equipo = get_object_or_404(_EQUIPO, pk=pk)
    datos, dorsal = datos_a_medias(request.POST)
    hallazgos = inscripcion.revisar_jugador(
        equipo, datos, dorsal, hoy=timezone.localdate(), es_organizacion=_es_organizacion(request)
    )
    if datos.nacimiento is None:
        hallazgos = [h for h in hallazgos if h.regla != "INS-02"]
    if not request.POST.get("dorsal"):
        hallazgos = [h for h in hallazgos if h.regla != "INS-09"]
    return _hallazgos(request, hallazgos)


@sensitive_post_parameters()
@sensitive_variables()
@requiere("torneo.inscribir_equipos", "cargar listas")
def agregar_profe(request: HttpRequest, pk: int) -> HttpResponse:
    equipo = get_object_or_404(_EQUIPO, pk=pk)
    formulario = FormularioProfe(request.POST or None, roles=_roles(equipo))
    hallazgos: list[Hallazgo] = []
    if request.method == "POST" and formulario.is_valid():
        resultado = inscripcion.agregar_profe(
            equipo,
            formulario.datos(),
            formulario.cleaned_data["rol"],
            hoy=timezone.localdate(),
            es_organizacion=_es_organizacion(request),
        )
        if resultado.guardado:
            return _avisar(request, formulario.cleaned_data["nombres"], resultado)
        hallazgos = resultado.hallazgos
    return render(
        request,
        "equipos/agregar.html",
        {"equipo": equipo, "form": formulario, "hallazgos": hallazgos, "que": "profe"},
    )


@require_POST
@sensitive_post_parameters()
@sensitive_variables()
@requiere("torneo.inscribir_equipos", "cargar listas")
def revisar_profe(request: HttpRequest, pk: int) -> HttpResponse:
    equipo = get_object_or_404(_EQUIPO, pk=pk)
    datos, _ = datos_a_medias(request.POST)
    rol = request.POST.get("rol") or _roles(equipo)[0]
    return _hallazgos(
        request,
        inscripcion.revisar_profe(
            equipo, datos, rol, hoy=timezone.localdate(), es_organizacion=_es_organizacion(request)
        ),
    )


@require_POST
@requiere("torneo.verificar_jugadores", "verificar jugadores")
def verificar(request: HttpRequest, pk: int) -> HttpResponse:
    """INS-12: la mesa marca al jugador al ver el documento original (o lo desmarca)."""
    jugador = get_object_or_404(Jugador.objects.select_related("persona"), pk=pk)
    jugador.verificado = not jugador.verificado
    jugador.save(update_fields=["verificado"])
    if pide_fragmento(request):
        return render(request, "equipos/_jugador.html", {"jugador": jugador})
    return redirect("equipo", pk=jugador.equipo_id, seccion="plantel")
