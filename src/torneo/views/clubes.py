"""Clubes (T11.6, P10): la organización los crea, los edita y une los duplicados."""

from django import forms
from django.contrib import messages
from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from torneo.models import Club, EquipoDeClub, Torneo
from torneo.permisos import requiere
from torneo.presentacion import escudo, olvidar_escudos
from torneo.servicios.clubes import NoSePuede, borrar_club, crear_club, editar_club, unir_clubes
from torneo.servicios.equipos import renombrar_equipo
from torneo.servicios.pendientes import sin_escudo_del_torneo
from torneo.views.confirmar import confirmado, pedir_confirmacion


class FormularioClub(forms.Form):
    nombre = forms.CharField(max_length=80)
    alias = forms.CharField(
        required=False,
        label="Otros nombres",
        help_text="Uno por línea. Sirven para reconocerlo al pegar listas.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )


@requiere("torneo.inscribir_equipos", "cambiar los clubes")
def clubes(request: HttpRequest) -> HttpResponse:
    formulario = FormularioClub(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        try:
            club = crear_club(formulario.cleaned_data["nombre"], formulario.cleaned_data["alias"])
        except NoSePuede as error:
            formulario.add_error("nombre", str(error))
        else:
            messages.success(request, f"{club} agregado")
            return redirect("clubes")
    lista = [
        {"club": c}
        for c in Club.objects.annotate(cantidad=Count("equipos_del_club")).order_by("nombre")
    ]
    return render(request, "clubes/lista.html", {"lista": lista, "form": formulario})


@requiere("torneo.inscribir_equipos", "cambiar los clubes")
def club(request: HttpRequest, pk: int) -> HttpResponse:
    actual = get_object_or_404(Club, pk=pk)
    formulario = FormularioClub(
        request.POST or None,
        initial={"nombre": actual.nombre, "alias": "\n".join(actual.alias)},
    )
    if request.method == "POST" and formulario.is_valid():
        try:
            editar_club(actual, formulario.cleaned_data["nombre"], formulario.cleaned_data["alias"])
        except NoSePuede as error:
            formulario.add_error("nombre", str(error))
        else:
            messages.success(request, "Club guardado")
            return redirect("clubes")
    return render(
        request,
        "clubes/club.html",
        {
            "club": actual,
            "form": formulario,
            "equipos": _equipos_del_club(actual),
            "otros": Club.objects.exclude(pk=actual.pk),
        },
    )


def _equipos_del_club(club: Club) -> list[dict[str, object]]:
    """Cada equipo del club con su escudo y las categorías en que juega (T13.1)."""
    filas = []
    for del_club in club.equipos_del_club.prefetch_related("equipos__categoria"):
        categorias = list(del_club.equipos.all())
        muestra = categorias[0] if categorias else None
        filas.append(
            {
                "id": str(del_club.pk),
                "del_club": del_club,
                "categorias": categorias,
                "escudo": escudo(muestra) if muestra else {"sigla": "", "url": ""},
            }
        )
    return filas


@requiere("torneo.configurar_torneo", "cambiar los escudos")
def sin_escudo(request: HttpRequest, pk: int) -> HttpResponse:
    """T13.2 (P88): los equipos del torneo sin escudo, cada uno con su botón para subirlo."""
    torneo = get_object_or_404(Torneo, pk=pk)
    equipos = [
        {
            "id": str(d.pk),
            "del_club": d,
            "categorias": list(
                d.equipos.filter(categoria__torneo=torneo).select_related("categoria")
            ),
        }
        for d in sin_escudo_del_torneo(torneo)
    ]
    titulo = f"Faltan {len(equipos)}" if equipos else "Sin pendientes"
    return render(
        request, "clubes/sin_escudo.html", {"torneo": torneo, "equipos": equipos, "titulo": titulo}
    )


@require_POST
@requiere("torneo.inscribir_equipos", "cambiar los clubes")
def renombrar(request: HttpRequest, pk: int) -> HttpResponse:
    """El nombre de un equipo del club, en todas sus categorías (T13.1)."""
    del_club = get_object_or_404(EquipoDeClub, pk=pk)
    try:
        renombrar_equipo(del_club, request.POST.get("nombre", ""))
    except NoSePuede as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Equipo renombrado: {del_club.nombre}")
    return redirect("club", pk=del_club.club_id)


@require_POST
@requiere("torneo.inscribir_equipos", "unir clubes")
def unir(request: HttpRequest, pk: int) -> HttpResponse:
    repetido = get_object_or_404(Club, pk=pk)
    destino = Club.objects.filter(pk=request.POST.get("destino") or 0).first()
    if destino is None:
        messages.error(request, "Elige con qué club unirlo.")
        return redirect("club", pk=pk)
    try:
        unidos = unir_clubes(repetido, destino)
    except NoSePuede as error:
        messages.error(request, str(error))
        return redirect("club", pk=pk)
    olvidar_escudos()
    messages.success(request, f"{repetido.nombre} unido a {destino.nombre}")
    if unidos:
        messages.warning(
            request,
            "Tenían equipos con el mismo nombre y quedaron unidos en uno: " + ", ".join(unidos),
        )
    return redirect("clubes")


@require_POST
@requiere("torneo.configurar_torneo", "borrar clubes")
def borrar(request: HttpRequest, pk: int) -> HttpResponse:
    """T13.3: solo un club sin equipos inscritos."""
    actual = get_object_or_404(Club, pk=pk)
    if not confirmado(request):
        return pedir_confirmacion(
            request,
            mensaje=f"Se borra el club {actual.nombre}.",
            boton="Borrar el club",
            volver=reverse("club", args=[pk]),
            peligro=True,
        )
    try:
        borrar_club(actual)
    except NoSePuede as error:
        messages.error(request, str(error))
        return redirect("club", pk=pk)
    olvidar_escudos()
    messages.success(request, f"{actual.nombre} borrado")
    return redirect("clubes")
