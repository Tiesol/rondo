"""Pantalla Torneo: una categoría-nivel con sus pestañas (TU.5).

Cambiar de categoría o de pestaña usa HTMX: con HX-Request se devuelve solo #categoria y la
URL se actualiza (hx-push-url), así se puede compartir o volver atrás.
"""

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from torneo.forms.categoria import FormularioAjustes, FormularioNuevaCategoria
from torneo.models import CategoriaNivel, Torneo
from torneo.permisos import requiere, sin_permiso
from torneo.presentacion import nacidos_en, resumen_de_categoria
from torneo.servicios.categorias import NoSePuede, agregar_categoria, nombres_de_la_plantilla
from torneo.servicios.copas import copas_por_club
from torneo.servicios.tabla import registrar_sorteo, tablas_de
from torneo.views.equipos import filas_de_equipos
from torneo.views.fixture import datos_del_fixture
from torneo.views.fragmentos import pide_fragmento

PESTANAS = {
    "equipos": "Equipos",
    "fixture": "Fixture",
    "posiciones": "Posiciones",
    "ajustes": "Ajustes",
}


def torneo(request: HttpRequest) -> HttpResponse:
    activo = Torneo.activo()
    primera = activo.categorias.first() if activo else None
    if primera is None:
        return redirect("inicio")
    return redirect("categoria", pk=primera.pk, pestana="equipos")


def categoria(request: HttpRequest, pk: int, pestana: str) -> HttpResponse:
    if pestana not in PESTANAS:
        raise Http404
    actual = get_object_or_404(CategoriaNivel.objects.select_related("torneo"), pk=pk)
    puede_cambiar = request.user.has_perm("torneo.configurar_torneo")

    formulario = None
    if pestana == "ajustes":
        if request.method == "POST" and not puede_cambiar:
            return sin_permiso(request, "cambiar los ajustes de una categoría")
        if puede_cambiar:
            formulario = FormularioAjustes(request.POST or None, instance=actual)
            if request.method == "POST" and formulario.is_valid():
                formulario.save()
                messages.success(request, f"Ajustes de {actual} guardados")
                return redirect("categoria", pk=actual.pk, pestana="ajustes")

    contexto = {
        "categoria": actual,
        "nombre": str(actual),
        "pestana": pestana,
        "resumen": resumen_de_categoria(actual),
        "nacidos": nacidos_en(actual),
        "canchas": " o ".join(c.codigo for c in actual.canchas.all()) or "Ninguna",
        "nivel": "" if actual.nivel == CategoriaNivel.Nivel.UNICO else actual.get_nivel_display(),
        "categorias": [
            {
                "texto": str(c),
                "url": reverse("categoria", args=[c.pk, pestana]),
                "actual": c.pk == actual.pk,
            }
            for c in actual.torneo.categorias.all()
        ],
        "pestanas": [
            {
                "texto": texto,
                "url": reverse("categoria", args=[actual.pk, clave]),
                "actual": clave == pestana,
            }
            for clave, texto in PESTANAS.items()
        ],
        "form": formulario,
        "puede_cambiar": puede_cambiar,
        "equipos": filas_de_equipos(actual) if pestana == "equipos" else [],
        "fixture": (
            datos_del_fixture(
                actual, con_propuesta=request.user.has_perm("torneo.configurar_torneo")
            )
            if pestana == "fixture"
            else {}
        ),
        "tablas": tablas_de(actual) if pestana == "posiciones" else [],
    }
    plantilla = "torneo/_categoria.html" if pide_fragmento(request) else "torneo/categoria.html"
    return render(request, plantilla, contexto)


@require_POST
@requiere("torneo.configurar_torneo", "registrar el sorteo")
def sorteo(request: HttpRequest, pk: int) -> HttpResponse:
    """P28: el lugar que salió para cada equipo empatado."""
    categoria = get_object_or_404(CategoriaNivel.objects.select_related("torneo"), pk=pk)
    lugares = []
    for equipo in categoria.equipos.all():
        valor = request.POST.get(f"lugar_{equipo.pk}", "")
        if valor.isdigit():
            lugares.append((int(valor), equipo.nombre, equipo))
    registrar_sorteo(categoria, [equipo for _, _, equipo in sorted(lugares)])
    messages.success(request, "Sorteo guardado")
    return redirect("categoria", pk=categoria.pk, pestana="posiciones")


@requiere("torneo.configurar_torneo", "agregar categorías")
def nueva_categoria(request: HttpRequest, pk: int) -> HttpResponse:
    """T11.1: una categoría o un nivel más en un torneo ya creado."""
    torneo_ = get_object_or_404(Torneo, pk=pk)
    formulario = FormularioNuevaCategoria(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        datos = formulario.cleaned_data
        try:
            nueva = agregar_categoria(
                torneo_,
                datos["nombre"],
                datos["nivel"],
                modalidad=datos["modalidad"],
                min_por_tiempo=datos["min_por_tiempo"],
                minimo=datos["minimo"],
                maximo=datos["maximo"],
            )
        except NoSePuede as error:
            formulario.add_error(None, str(error))
        else:
            messages.success(request, f"{nueva} agregada: revisa sus ajustes")
            return redirect("categoria", pk=nueva.pk, pestana="ajustes")
    volver = torneo_.categorias.first()
    return render(
        request,
        "torneo/nueva_categoria.html",
        {
            "torneo": torneo_,
            "form": formulario,
            "sugeridas": nombres_de_la_plantilla(),
            "volver": volver,
        },
    )


def copas(request: HttpRequest, pk: int) -> HttpResponse:
    """T13.24 (P30): qué copas ganó cada club. Para cualquiera con sesión."""
    torneo = get_object_or_404(Torneo, pk=pk)
    return render(request, "torneo/copas.html", {"torneo": torneo, "filas": copas_por_club(torneo)})
