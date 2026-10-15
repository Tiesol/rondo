"""Editar los cruces del fixture a mano (T13.22).

Dos operaciones, por fecha: rearmar la fecha (quién juega con quién en cada uno de sus partidos)
e intercambiarla con otra. Bloquea lo que no puede ser: un equipo con dos partidos en la misma
fecha, un cruce que el formato no tiene (en series, de dos series; en series cruzadas, de la
misma serie) o una fecha con partidos ya jugados. Lo demás se avisa, sin bloquear: a quién le
falta jugar con quién y qué cruce se repite, hasta que el fixture vuelve a estar completo.
El día y la hora no cambian: eso sigue con Mover e Intercambiar.
"""

from collections import Counter
from itertools import combinations
from typing import Any

from django.db import transaction

from torneo.models import CategoriaNivel, Equipo, Partido
from torneo.servicios.clubes import NoSePuede
from torneo.servicios.fixture import formatos
from torneo.servicios.historial import registrar


def _grupos(categoria: CategoriaNivel) -> tuple[str, int, dict[int, str]]:
    """El tipo de grupos del formato, cuántas veces se enfrenta cada par y la serie de cada
    equipo."""
    grupos = formatos().para(categoria.equipos.count()).grupos
    serie_de = {
        e.pk: serie.nombre for serie in categoria.series.prefetch_related("equipos")
        for e in serie.equipos.all()
    }  # fmt: skip
    return grupos.tipo, 2 if grupos.ida_y_vuelta else 1, serie_de


def _fuera_del_formato(tipo: str, serie_de: dict[int, str], a: int, b: int) -> str:
    """Por qué el formato no tiene el cruce de los equipos `a` y `b`, o ""."""
    misma = serie_de.get(a) == serie_de.get(b)
    if tipo == "series" and not misma:
        return "son de series distintas: no se enfrentan en grupos"
    if tipo == "series_cruzadas" and misma:
        return "son de la misma serie: en series cruzadas, cada equipo juega con la otra serie"
    return ""


def _sin_jugados(partidos: list[Partido]) -> None:
    for p in partidos:
        if p.empezado or p.no_se_presento:
            raise NoSePuede(f"{p} ya se jugó: su fecha no se cambia.")


@transaction.atomic
def rearmar_fecha(
    categoria: CategoriaNivel,
    fecha: int,
    nuevos: dict[int, tuple[Equipo | None, Equipo | None]],
    usuario: Any,
) -> None:
    """`nuevos` es {pk del partido: (local, visitante)} para los partidos de la fecha que
    cambian; los demás quedan como están."""
    partidos = list(
        categoria.partidos.filter(fase=Partido.Fase.GRUPOS, fecha=fecha).select_related(
            "local", "visitante"
        )
    )
    por_pk = {p.pk: p for p in partidos}
    if ajenos := set(nuevos) - set(por_pk):
        raise NoSePuede(f"{len(ajenos)} partido(s) no son de la fecha {fecha}.")
    cambian = [por_pk[pk] for pk in nuevos]
    _sin_jugados(cambian)
    del_torneo = set(categoria.equipos.values_list("pk", flat=True))
    tipo, _, serie_de = _grupos(categoria)
    quedan: dict[int, tuple[Equipo, Equipo]] = {}
    for p in partidos:
        local, visitante = nuevos.get(p.pk, (p.local, p.visitante))
        if local is None or visitante is None:
            raise NoSePuede("Elige los dos equipos de cada partido.")
        if local.pk == visitante.pk:
            raise NoSePuede(f"{local.nombre} no puede jugar contra sí mismo.")
        if {local.pk, visitante.pk} - del_torneo:
            raise NoSePuede(f"Los equipos tienen que ser de {categoria}.")
        if motivo := _fuera_del_formato(tipo, serie_de, local.pk, visitante.pk):
            raise NoSePuede(f"{local.nombre} y {visitante.nombre} {motivo}.")
        quedan[p.pk] = (local, visitante)
    veces = Counter(e.nombre for par in quedan.values() for e in par)
    if repetidos := sorted(n for n, cuantas in veces.items() if cuantas > 1):
        raise NoSePuede(f"{repetidos[0]} juega dos partidos en la fecha {fecha}.")
    for p in cambian:
        local, visitante = quedan[p.pk]
        if (p.local_id, p.visitante_id) == (local.pk, visitante.pk):
            continue
        antes = (
            f"{p.local.nombre if p.local else ''} vs {p.visitante.nombre if p.visitante else ''}"
        )
        p.local, p.visitante, p.editado_a_mano = local, visitante, True
        if tipo == "series" and serie_de.get(local.pk):
            p.serie = categoria.series.get(nombre=serie_de[local.pk])
        p.save(update_fields=["local", "visitante", "editado_a_mano", "serie"])
        registrar(
            p,
            usuario,
            "Cruce cambiado a mano",
            antes=antes[:80],
            despues=f"{local.nombre} vs {visitante.nombre}"[:80],
        )


@transaction.atomic
def intercambiar_fechas(categoria: CategoriaNivel, una: int, otra: int, usuario: Any) -> None:
    """Los cruces de la fecha `una` pasan a `otra` y viceversa (el día y la hora no cambian)."""
    if una == otra:
        raise NoSePuede("Elige otra fecha.")
    grupos = categoria.partidos.filter(fase=Partido.Fase.GRUPOS)
    de_una, de_otra = list(grupos.filter(fecha=una)), list(grupos.filter(fecha=otra))
    if not de_una or not de_otra:
        raise NoSePuede("Esa fecha no existe.")
    _sin_jugados(de_una + de_otra)
    for partidos, nueva in ((de_una, otra), (de_otra, una)):
        for p in partidos:
            p.fecha, p.editado_a_mano = nueva, True
            p.save(update_fields=["fecha", "editado_a_mano"])
            registrar(
                p,
                usuario,
                "Cruce: cambio de fecha",
                antes=str(otra if nueva == una else una),
                despues=str(nueva),
            )


def avisos_del_fixture(categoria: CategoriaNivel) -> list[str]:
    """A quién le falta jugar con quién y qué cruce se repite (no bloquean)."""
    equipos = {e.pk: e.nombre for e in categoria.equipos.all()}
    if len(equipos) < 2 or not categoria.partidos.filter(fase=Partido.Fase.GRUPOS).exists():
        return []
    try:
        tipo, veces_esperadas, serie_de = _grupos(categoria)
    except ValueError:
        return []
    esperados = Counter(
        frozenset(par)
        for par in combinations(sorted(equipos), 2)
        if not _fuera_del_formato(tipo, serie_de, *par)
        for _ in range(veces_esperadas)
    )
    hay = Counter(
        frozenset((p.local_id, p.visitante_id))
        for p in categoria.partidos.filter(fase=Partido.Fase.GRUPOS)
        if p.local_id and p.visitante_id
    )

    def nombres(par: frozenset[int]) -> tuple[str, str]:
        a, b = sorted(par, key=lambda pk: equipos.get(pk, ""))
        return equipos.get(a, "?"), equipos.get(b, "?")

    avisos = [
        "{} vs {} está repetido.".format(*nombres(par))
        for par, cuantas in sorted(hay.items(), key=lambda x: nombres(x[0]))
        if cuantas > esperados.get(par, 0)
    ]
    avisos += [
        "{} todavía no juega con {}.".format(*nombres(par))
        for par, cuantas in sorted(esperados.items(), key=lambda x: nombres(x[0]))
        if hay.get(par, 0) < cuantas
    ]
    return avisos
