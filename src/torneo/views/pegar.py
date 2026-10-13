"""Pegar una lista de jugadores o del cuerpo técnico (T7.8 y T7.9).

La organización abre la lista que mandó el club (Excel, Word o un PDF pasado a Excel), copia
las filas y las pega. Tres pasos: pegar, elegir qué es cada columna y la vista previa, que se
puede corregir antes de guardar.

Son datos personales de menores: viajan solo en el formulario (nunca en la sesión), el
formulario es sensible y el log no registra cuerpos de requests.
"""

from typing import Any, cast

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables

from dominio.config import CuerpoTecnico
from dominio.pegado import (
    CAMPOS,
    COLUMNAS,
    Analisis,
    Columna,
    FilaLeida,
    analizar,
    campos_de_filas,
    leer_campos,
    leer_filas,
)
from torneo.models import Equipo
from torneo.permisos import requiere
from torneo.servicios import inscripcion
from torneo.servicios.pegado import MAX_FILAS, FilaCargada, Que, cargar_lista

_EQUIPO = Equipo.objects.select_related("club", "categoria__torneo")
_SECCION: dict[Que, str] = {"jugadores": "plantel", "profes": "cuerpo-tecnico"}
# Lo que no tiene sentido en cada lista no se ofrece como columna.
_SIN: dict[Que, set[str]] = {"jugadores": {"rol"}, "profes": {"nacimiento", "dorsal"}}


def _opciones(que: Que) -> list[tuple[str, str]]:
    return [(clave, texto) for clave, texto in COLUMNAS.items() if clave not in _SIN[que]]


def _columnas_elegidas(post: Any, analisis: Analisis, que: Que) -> list[Columna]:
    validas = {clave for clave, _ in _opciones(que)}
    elegidas = []
    for i, propuesta in enumerate(analisis.columnas):
        valor = post.get(f"col{i}", propuesta)
        elegidas.append(cast(Columna, valor if valor in validas else "ignorar"))
    return elegidas


def _filas_del_formulario(post: Any) -> list[tuple[int, dict[str, str]]]:
    try:
        cantidad = min(int(post.get("n", "0")), MAX_FILAS)
    except ValueError:
        cantidad = 0
    filas = []
    for i in range(cantidad):
        try:
            numero = int(post.get(f"f{i}-numero", i + 1))
        except ValueError:
            numero = i + 1
        filas.append((numero, {campo: post.get(f"f{i}-{campo}", "") for campo in CAMPOS}))
    return filas


@sensitive_post_parameters()
@sensitive_variables()
@requiere("torneo.inscribir_equipos", "cargar listas")
def pegar(request: HttpRequest, pk: int, que: str) -> HttpResponse:
    if que not in _SECCION:
        raise Http404
    lista: Que = que  # `in _SECCION` ya lo acota
    equipo = get_object_or_404(_EQUIPO, pk=pk)
    roles = CuerpoTecnico.model_validate(equipo.categoria.torneo.cuerpo_tecnico).roles
    contexto: dict[str, Any] = {
        "equipo": equipo,
        "que": lista,
        "volver": f"/equipos/{equipo.pk}/{_SECCION[lista]}/",
        "paso": "texto",
        "max_filas": MAX_FILAS,
    }
    paso = request.POST.get("paso") if request.method == "POST" else None
    texto = request.POST.get("texto", "")

    if paso == "columnas" or (paso == "revisar" and "texto" in request.POST):
        analisis = analizar(texto, roles)
        validas = {clave for clave, _ in _opciones(lista)}
        analisis = analisis.con_columnas(
            [c if c in validas else "ignorar" for c in analisis.columnas]
        )
        if not analisis.filas:
            messages.error(request, "No hay filas: pega las filas de la lista.")
            return render(request, "equipos/pegar.html", contexto | {"texto": texto})
        if len(analisis.filas) > MAX_FILAS:
            messages.error(
                request,
                f"Son {len(analisis.filas)} filas: el máximo es {MAX_FILAS}. "
                "Pega la lista de un solo equipo.",
            )
            return render(request, "equipos/pegar.html", contexto | {"texto": texto})
        if paso == "columnas":
            return render(
                request,
                "equipos/pegar.html",
                contexto
                | {
                    "paso": "columnas",
                    "texto": texto,
                    "analisis": analisis,
                    "selectores": [
                        (
                            f"col{i}",
                            c,
                            analisis.encabezado[i] if analisis.encabezado else "",
                            [fila[i] for fila in analisis.filas if fila[i]][:3],
                        )
                        for i, c in enumerate(analisis.columnas)
                    ],
                    "opciones": _opciones(lista),
                },
            )
        analisis = analisis.con_columnas(_columnas_elegidas(request.POST, analisis, lista))
        leidas = list(zip(leer_filas(analisis, roles), campos_de_filas(analisis), strict=True))
        if analisis.aviso_fechas:
            messages.warning(request, analisis.aviso_fechas)
        guardar = False
    elif paso in ("revisar", "guardar"):
        leidas = [
            (leer_campos(numero, campos, orden="dma", roles=roles), campos)
            for numero, campos in _filas_del_formulario(request.POST)
        ]
        guardar = paso == "guardar"
    else:  # el primer paso, o "Volver" desde las columnas con el texto pegado
        return render(request, "equipos/pegar.html", contexto | {"texto": texto})

    filas = _cargar(request, equipo, leidas, lista, guardar=guardar, roles=roles)
    if guardar:
        guardadas = sum(f.guardada for f in filas)
        if guardadas:
            messages.success(
                request, f"Se guardaron {guardadas} {'fila' if guardadas == 1 else 'filas'}."
            )
        filas = [f for f in filas if not f.guardada]
        if not filas:
            return redirect("equipo", pk=equipo.pk, seccion=_SECCION[lista])
    return render(
        request,
        "equipos/pegar.html",
        contexto
        | {
            "paso": "vista",
            "filas": filas,
            "listas": sum(f.guardada for f in filas) if not guardar else 0,
            "con_errores": sum(bool(f.errores) for f in filas),
        },
    )


def _cargar(
    request: HttpRequest,
    equipo: Equipo,
    leidas: list[tuple[FilaLeida, dict[str, str]]],
    que: Que,
    *,
    guardar: bool,
    roles: tuple[str, ...],
) -> list[FilaCargada]:
    return cargar_lista(
        equipo,
        leidas,
        que,
        ahora=inscripcion.ahora_local(),
        guardar=guardar,
        roles=roles,
    )
