"""Lo que necesita atención en el torneo, para la lista de Inicio (TU.5).

Sin barra de avance: solo pendientes concretos, cada uno con un enlace a donde se resuelve.
Categorías sin equipos o que no se abren, equipos debajo del mínimo o sin escudo, fixtures que
faltan o están desactualizados, y partidos sin programar.
"""

from collections.abc import Iterable
from typing import Any

from django.db.models import Count
from django.urls import reverse

from torneo.models import Equipo, EquipoDeClub, Partido, Torneo
from torneo.servicios.bloqueos import chocan_con_bloqueos
from torneo.servicios.fixture import formatos, motivo_desactualizado


def pendientes(torneo: Torneo, *, puede_configurar: bool) -> list[dict[str, Any]]:
    lista: list[dict[str, Any]] = []

    categorias = torneo.categorias.annotate(cantidad=Count("equipos"))
    sin_equipos = [c for c in categorias if c.cantidad == 0]
    if sin_equipos:
        lista.append(
            {
                "titulo": _contar(
                    len(sin_equipos), "categoría sin equipos", "categorías sin equipos"
                ),
                "sub": _primeros(str(c) for c in sin_equipos),
                "url": reverse("categoria", args=[sin_equipos[0].pk, "equipos"]),
                "icono": "torneo",
                "estado": "aviso",
            }
        )

    cortos = [
        e
        for e in Equipo.objects.filter(categoria__torneo=torneo)
        .select_related("categoria")
        .annotate(cantidad=Count("jugadores"))
        if e.cantidad < e.categoria.min_jugadores
    ]
    if cortos:
        lista.append(
            {
                "titulo": _contar(
                    len(cortos),
                    "equipo debajo del mínimo de jugadores",
                    "equipos debajo del mínimo de jugadores",
                ),
                "sub": _primeros(f"{e.nombre} ({e.categoria})" for e in cortos),
                "url": reverse("equipo", args=[cortos[0].pk, "plantel"]),
                "icono": "personas",
                "estado": "aviso",
            }
        )

    minimo = formatos().minimo_equipos
    no_se_abren = list(
        torneo.categorias.annotate(cantidad=Count("equipos", distinct=True)).filter(
            cantidad__gt=0, cantidad__lt=minimo
        )
    )
    if no_se_abren:
        lista.append(
            {
                "titulo": _contar(
                    len(no_se_abren),
                    f"categoría no se abre: tiene {no_se_abren[0].cantidad} equipo"
                    + ("s" if no_se_abren[0].cantidad != 1 else ""),
                    f"categorías no se abren: tienen menos de {minimo} equipos",
                ),
                "sub": _primeros(str(c) for c in no_se_abren),
                "url": reverse("categoria", args=[no_se_abren[0].pk, "fixture"]),
                "icono": "info",
                "estado": "info",
            }
        )

    sin_fixture = list(
        torneo.categorias.annotate(cantidad=Count("equipos", distinct=True))
        .filter(cantidad__gte=minimo, partidos__isnull=True)
        .distinct()
    )
    if sin_fixture:
        lista.append(
            {
                "titulo": _contar(
                    len(sin_fixture), "categoría sin fixture", "categorías sin fixture"
                ),
                "sub": _primeros(str(c) for c in sin_fixture),
                "url": reverse("categoria", args=[sin_fixture[0].pk, "fixture"]),
                "icono": "calendario",
                "estado": "info",
            }
        )

    desactualizadas = [
        c
        for c in torneo.categorias.select_related("torneo").prefetch_related("partidos", "equipos")
        if motivo_desactualizado(c, list(c.partidos.all()), {e.pk for e in c.equipos.all()})
    ]
    if desactualizadas:
        lista.append(
            {
                "titulo": _contar(
                    len(desactualizadas),
                    "categoría con el fixture desactualizado",
                    "categorías con el fixture desactualizado",
                ),
                "sub": _primeros(str(c) for c in desactualizadas),
                "url": reverse("categoria", args=[desactualizadas[0].pk, "fixture"]),
                "icono": "calendario",
                "estado": "aviso",
            }
        )

    if puede_configurar and (sin_escudo := sin_escudo_del_torneo(torneo)):
        lista.append(
            {
                "titulo": _contar(len(sin_escudo), "equipo sin escudo", "equipos sin escudo"),
                "sub": _primeros(d.nombre for d in sin_escudo),
                "url": reverse("sin-escudo", args=[torneo.pk]),
                "icono": "camara",
                "estado": "aviso",
            }
        )

    if puede_configurar and (con_bloqueo := chocan_con_bloqueos(torneo)):
        lista.append(
            {
                "titulo": _contar(
                    len(con_bloqueo),
                    "partido choca con un bloqueo",
                    "partidos chocan con un bloqueo",
                ),
                "sub": "Moverlo a mano, intercambiarlo o ver propuestas",
                "url": reverse("acf", args=[torneo.pk]),
                "icono": "aviso",
                "estado": "error",
            }
        )

    sin_programar = Partido.objects.filter(
        categoria__torneo=torneo, estado=Partido.Estado.PENDIENTE, inicio__isnull=True
    ).count()
    if puede_configurar and sin_programar:
        lista.append(
            {
                "titulo": _contar(
                    sin_programar, "partido sin día ni hora", "partidos sin día ni hora"
                ),
                "sub": "Programar los ubica en los días y las canchas",
                "url": reverse("programar", args=[torneo.pk]),
                "icono": "calendario",
                "estado": "aviso",
            }
        )
    return lista


def sin_escudo_del_torneo(torneo: Torneo) -> list[EquipoDeClub]:
    """Los equipos del club que juegan en el torneo y no tienen escudo (P88: no bloquea nada)."""
    return list(
        EquipoDeClub.objects.filter(escudo="", equipos__categoria__torneo=torneo)
        .select_related("club")
        .distinct()
        .order_by("club__nombre", "nombre")
    )


def _contar(cantidad: int, singular: str, plural: str) -> str:
    return f"{cantidad} {singular if cantidad == 1 else plural}"


def _primeros(nombres: Iterable[str], cuantos: int = 3) -> str:
    """ "A, B y C", o "A, B, C y 4 más"."""
    lista = list(nombres)
    if len(lista) > cuantos:
        return f"{', '.join(lista[:cuantos])} y {len(lista) - cuantos} más"
    return lista[0] if len(lista) == 1 else f"{', '.join(lista[:-1])} y {lista[-1]}"
