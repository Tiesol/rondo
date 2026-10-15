"""Equipos: renombrar (T13.1), borrar y corregir uno mal cargado (T13.3).

El nombre vive en EquipoDeClub; cada Equipo (una categoría) guarda una copia del nombre y del
club, que se cambia acá y en la misma transacción.
"""

from django.db import transaction
from django.db.models import Q, QuerySet

from torneo.models import CategoriaNivel, Club, Convocado, Equipo, EquipoDeClub, Partido, Persona
from torneo.servicios.clubes import NoSePuede, borrar_si_nadie_los_usa


@transaction.atomic
def renombrar_equipo(del_club: EquipoDeClub, nombre: str) -> None:
    nombre = nombre.strip()
    if not nombre:
        raise NoSePuede("Escribe el nombre del equipo.")
    otros = EquipoDeClub.objects.filter(club_id=del_club.club_id, nombre__iexact=nombre)
    if otros.exclude(pk=del_club.pk).exists():
        raise NoSePuede(f"{del_club.club} ya tiene un equipo llamado {nombre}.")
    del_club.nombre = nombre
    del_club.save(update_fields=["nombre"])
    Equipo.objects.filter(equipo_de_club=del_club).update(nombre=nombre)


def partidos_de(equipo: Equipo) -> QuerySet[Partido]:
    return Partido.objects.filter(Q(local=equipo) | Q(visitante=equipo))


def jugados_de(equipo: Equipo) -> QuerySet[Partido]:
    """Los partidos que empezaron, terminaron o se dieron por W.O.: esos no se borran."""
    return partidos_de(equipo).filter(
        Q(estado__in=[Partido.Estado.EN_JUEGO, Partido.Estado.JUGADO]) | ~Q(no_se_presento="")
    )


def _sin_jugados(equipo: Equipo, que: str) -> None:
    if jugados_de(equipo).exists():
        raise NoSePuede(
            f"{equipo.nombre} ya tiene partidos jugados en {equipo.categoria}: no se puede "
            f"{que}. Se puede retirar del torneo."
        )


def _sacar_del_fixture(equipo: Equipo) -> None:
    """Sus partidos de grupos se borran y en la eliminación su lugar queda por definir. El
    fixture de la categoría queda desactualizado, y el pendiente de Inicio lo dice."""
    partidos = partidos_de(equipo)
    Convocado.objects.filter(equipo=equipo).delete()
    partidos.filter(fase=Partido.Fase.GRUPOS).delete()
    Partido.objects.filter(local=equipo).update(local=None)
    Partido.objects.filter(visitante=equipo).update(visitante=None)
    for serie in equipo.series.all():
        serie.equipos.remove(equipo)


def _borrar_huerfano(del_club: EquipoDeClub) -> None:
    """El equipo del club que quedó sin categorías se borra, con su escudo si nadie más lo usa."""
    if del_club.equipos.exists():
        return
    escudo = del_club.escudo.name
    del_club.delete()
    if escudo:
        borrar_si_nadie_los_usa([escudo])


def resumen_para_borrar(equipo: Equipo) -> list[str]:
    """Lo que se borra con el equipo, para el "¿Estás seguro?"."""
    jugadores = equipo.jugadores.count()
    profes = equipo.profes.count()
    partidos = partidos_de(equipo).filter(fase=Partido.Fase.GRUPOS).count()
    detalle = [
        f"{jugadores} jugador{'es' if jugadores != 1 else ''} del plantel",
        f"{profes} persona{'s' if profes != 1 else ''} del cuerpo técnico",
    ]
    if partidos:
        detalle.append(
            f"{partidos} partido{'s' if partidos != 1 else ''} sin jugar: el fixture de "
            f"{equipo.categoria} queda desactualizado y hay que rehacerlo"
        )
    return detalle


@transaction.atomic
def borrar_equipo(equipo: Equipo) -> None:
    """T13.3: solo sin partidos jugados. Se borran su plantel y su cuerpo técnico en ese torneo,
    y las personas que no están en ningún otro equipo (son datos de menores)."""
    _sin_jugados(equipo, "borrar")
    _sacar_del_fixture(equipo)
    personas = set(equipo.jugadores.values_list("persona", flat=True)) | set(
        equipo.profes.values_list("persona", flat=True)
    )
    del_club = equipo.equipo_de_club
    equipo.delete()
    sueltas = Persona.objects.filter(pk__in=personas, jugadores__isnull=True, profes__isnull=True)
    fotos = [p.foto.name for p in sueltas if p.foto.name]
    sueltas.delete()
    if fotos:
        storage = Persona().foto.storage

        def borrar_fotos() -> None:
            for foto in fotos:
                storage.delete(foto)

        transaction.on_commit(borrar_fotos)
    _borrar_huerfano(del_club)


@transaction.atomic
def cambiar_equipo(equipo: Equipo, *, club: Club, categoria: CategoriaNivel, nombre: str) -> None:
    """Corregir un equipo mal cargado (T13.3): otro club, otra categoría u otro nombre, mientras
    no tenga partidos jugados. Si cambia de categoría, sale del fixture de la vieja."""
    nombre = nombre.strip() or club.nombre
    otro_club = club.pk != equipo.club_id
    otro_nombre = nombre.casefold() != equipo.nombre.casefold()
    otra_categoria = categoria.pk != equipo.categoria_id
    if not (otro_club or otro_nombre or otra_categoria):
        return
    if otra_categoria or otro_club:
        _sin_jugados(equipo, "cambiar de club ni de categoría")
    viejo = equipo.equipo_de_club
    nuevo = EquipoDeClub.del_club(club, nombre) if (otro_club or otro_nombre) else viejo
    repetido = Equipo.objects.filter(equipo_de_club=nuevo, categoria=categoria)
    if repetido.exclude(pk=equipo.pk).exists():
        raise NoSePuede(f"Ya hay un equipo «{nuevo.nombre}» de {club} en {categoria}.")
    if otra_categoria:
        _sacar_del_fixture(equipo)
    Equipo.objects.filter(pk=equipo.pk).update(
        equipo_de_club=nuevo, club=nuevo.club, nombre=nuevo.nombre, categoria=categoria
    )
    equipo.refresh_from_db()
    if nuevo.pk != viejo.pk:
        _borrar_huerfano(viejo)
