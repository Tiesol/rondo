"""Capacidad del torneo (T3.7): lo que piden los partidos contra lo que dan las canchas.

Cuenta los partidos del fixture; si una categoría todavía no lo tiene, los estima con su
formato. Hay dos escenarios: todo el torneo, y la eliminación desde su fin de semana (P33).
"""

from dataclasses import dataclass, field

from django.db.models import Count
from django.utils import timezone

from dominio.capacidad import Demanda, GrupoDeCanchas, calcular_capacidad
from dominio.config import Reglas
from dominio.formatos import CategoriaNoSeAbre, FormatoFaltante
from torneo.models import Franja, Partido, Torneo
from torneo.servicios.fixture import formato_para


@dataclass
class Capacidad:
    total: list[GrupoDeCanchas]
    con_extra: list[GrupoDeCanchas]  # A4: lo mismo, sumando el tiempo agregado
    eliminacion: list[GrupoDeCanchas]
    eliminacion_desde: int  # número de fin de semana (1 es el primero)
    fines_de_semana: int
    estimadas: list[str] = field(default_factory=list)  # sin fixture: según su formato
    sin_formato: list[str] = field(default_factory=list)


def _cola_por_cancha(
    torneo: Torneo, reglas: Reglas, padres: dict[str, str | None]
) -> dict[str, int]:
    """Lo que dura el partido más largo que se juega en cada cancha entera."""
    cola: dict[str, int] = {}
    for categoria in torneo.categorias.prefetch_related("canchas"):
        for cancha in categoria.canchas.all():
            entera = padres.get(cancha.codigo) or cancha.codigo
            cola[entera] = max(cola.get(entera, 0), categoria.minutos_partido)
    return cola


def capacidad_del_torneo(torneo: Torneo) -> Capacidad:
    reglas = Reglas.model_validate(torneo.reglas)
    padres = {
        c.codigo: (c.padre.codigo if c.padre else None)
        for c in torneo.canchas.select_related("padre")
    }
    enteras = [codigo for codigo, padre in padres.items() if padre is None]

    # Franjas por fin de semana: la eliminación usa desde el que dice la regla (P33).
    vigentes = list(torneo.franjas.filter(suspendida=False).prefetch_related("canchas"))
    franjas = sorted((f for f in vigentes if f.tipo == Franja.Tipo.REGULAR), key=lambda f: f.inicio)
    extras = [f for f in vigentes if f.tipo == Franja.Tipo.ENTRE_SEMANA]
    semanas = sorted({timezone.localtime(f.inicio).isocalendar()[:2] for f in franjas})
    desde = reglas.eliminacion_desde_fin_de_semana
    semanas_de_eliminacion = set(semanas[desde - 1 :])
    # A5 (P48): con "último inicio", el último partido de cada franja empieza a la hora de
    # cierre y termina después: cada franja suma lo que dura un partido de esa cancha.
    cola = (
        _cola_por_cancha(torneo, reglas, padres) if reglas.fin_de_franja == "ultimo_inicio" else {}
    )

    def minutos(franja: Franja, cancha: str) -> int:
        return int((franja.fin - franja.inicio).total_seconds() // 60) + cola.get(cancha, 0)

    def oferta(solo_eliminacion: bool, con_extra: bool = False) -> dict[str, int]:
        oferta_total: dict[str, int] = {}
        for cancha in enteras:
            suma = sum(
                minutos(f, cancha)
                for f in franjas
                if not solo_eliminacion
                or timezone.localtime(f.inicio).isocalendar()[:2] in semanas_de_eliminacion
            )
            if con_extra:
                suma += sum(
                    minutos(f, cancha)
                    for f in extras
                    if not f.canchas.all() or cancha in {c.codigo for c in f.canchas.all()}
                )
            oferta_total[cancha] = suma
        return oferta_total

    resultado = Capacidad([], [], [], desde, len(semanas))
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
                formato = formato_para(reglas, cantidad)
            except CategoriaNoSeAbre:
                continue  # T13.7: no se juega
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
    resultado.con_extra = calcular_capacidad(
        total, padres, oferta(solo_eliminacion=False, con_extra=True)
    )
    resultado.eliminacion = calcular_capacidad(eliminacion, padres, oferta(solo_eliminacion=True))
    return resultado
