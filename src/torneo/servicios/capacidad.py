"""Capacidad del torneo (T3.7): lo que piden los partidos contra lo que dan las canchas.

Cuenta los partidos del fixture; si una categoría todavía no lo tiene, los estima con su
formato. Hay dos escenarios: todo el torneo, y la eliminación desde su fin de semana (P33).
"""

from dataclasses import dataclass, field

from django.db.models import Count
from django.utils import timezone

from dominio.capacidad import Demanda, GrupoDeCanchas, calcular_capacidad
from dominio.config import Reglas
from dominio.formatos import FormatoFaltante
from torneo.models import Partido, Torneo
from torneo.servicios.fixture import formatos


@dataclass
class Capacidad:
    total: list[GrupoDeCanchas]
    eliminacion: list[GrupoDeCanchas]
    eliminacion_desde: int  # número de fin de semana (1 es el primero)
    fines_de_semana: int
    estimadas: list[str] = field(default_factory=list)  # sin fixture: según su formato
    sin_formato: list[str] = field(default_factory=list)


def capacidad_del_torneo(torneo: Torneo) -> Capacidad:
    reglas = Reglas.model_validate(torneo.reglas)
    padres = {
        c.codigo: (c.padre.codigo if c.padre else None)
        for c in torneo.canchas.select_related("padre")
    }
    enteras = [codigo for codigo, padre in padres.items() if padre is None]

    # Franjas por fin de semana: la eliminación usa desde el que dice la regla (P33).
    franjas = list(torneo.franjas.filter(suspendida=False).order_by("inicio"))
    semanas = sorted({timezone.localtime(f.inicio).isocalendar()[:2] for f in franjas})
    desde = reglas.eliminacion_desde_fin_de_semana
    semanas_de_eliminacion = set(semanas[desde - 1 :])

    def oferta(solo_eliminacion: bool) -> dict[str, int]:
        minutos = sum(
            int((f.fin - f.inicio).total_seconds() // 60)
            for f in franjas
            if not solo_eliminacion
            or timezone.localtime(f.inicio).isocalendar()[:2] in semanas_de_eliminacion
        )
        return dict.fromkeys(enteras, minutos)

    resultado = Capacidad([], [], desde, len(semanas))
    total: list[Demanda] = []
    eliminacion: list[Demanda] = []
    categorias = torneo.categorias.prefetch_related("canchas").annotate(
        cantidad=Count("equipos", distinct=True)
    )
    por_fase = {
        (fila["categoria"], fila["fase"]): fila["n"]
        for fila in Partido.objects.filter(categoria__torneo=torneo)
        .values("categoria", "fase")
        .annotate(n=Count("pk"))
    }
    for categoria in categorias:
        grupos = por_fase.get((categoria.pk, Partido.Fase.GRUPOS), 0)
        llaves = por_fase.get((categoria.pk, Partido.Fase.ELIMINACION), 0)
        cantidad: int = categoria.cantidad
        if not grupos and not llaves and cantidad >= 2:
            try:
                formato = formatos().para(cantidad)
            except FormatoFaltante:
                resultado.sin_formato.append(str(categoria))
                continue
            grupos = formato.grupos.cantidad_de_partidos(cantidad)
            llaves = len(formato.eliminacion)
            resultado.estimadas.append(str(categoria))
        canchas = frozenset(c.codigo for c in categoria.canchas.all())
        turno = categoria.minutos_turno
        total.append(Demanda(str(categoria), (grupos + llaves) * turno, canchas))
        eliminacion.append(Demanda(str(categoria), llaves * turno, canchas))

    resultado.total = calcular_capacidad(total, padres, oferta(solo_eliminacion=False))
    resultado.eliminacion = calcular_capacidad(eliminacion, padres, oferta(solo_eliminacion=True))
    return resultado
