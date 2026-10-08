"""Por qué no entra un partido (PRO-14; ARQUITECTURA 8).

Para cada partido sin ubicar se prueban sus inicios y canchas posibles contra el calendario
que salió, y se cuenta qué bloquea a cada uno. El motivo es el que bloquea a más candidatos.
"""

from collections import Counter, defaultdict
from collections.abc import Hashable
from datetime import datetime, timedelta

from dominio.programador.modelo import PASO_MIN, PartidoAProgramar, Problema, Resultado

MOTIVOS = {
    "cancha": "No queda ningún turno libre en {canchas}",
    "equipo": "Sus equipos ya juegan en los turnos que quedan, o llegan al máximo del día",
    "persona": "Los turnos que quedan chocan con un profe o un jugador compartido",
    "bloqueo": "Los turnos que quedan caen en un bloqueo de la ACF",
    "orden": "No queda lugar después de los partidos que tiene que esperar",
}


def _se_pisan(a: datetime, fin_a: datetime, b: datetime, fin_b: datetime) -> bool:
    return a < fin_b and b < fin_a


class _Calendario:
    """Lo que ya quedó ubicado, ordenado para consultar rápido por día."""

    def __init__(self, problema: Problema, resultado: Resultado) -> None:
        self.problema = problema
        self.partidos = {p.id: p for p in problema.partidos}
        self.ubicados = resultado.ubicados
        self.por_dia: dict[object, list[PartidoAProgramar]] = defaultdict(list)
        for id_, (_, inicio) in resultado.ubicados.items():
            self.por_dia[inicio.date()].append(self.partidos[id_])

    def lugar(self, partido: PartidoAProgramar) -> tuple[str, datetime, datetime, datetime]:
        cancha, inicio = self.ubicados[partido.id]
        return (
            cancha,
            inicio,
            inicio + timedelta(minutes=partido.minutos_partido),
            inicio + timedelta(minutes=partido.minutos_turno),
        )

    def problemas(self, partido: PartidoAProgramar, cancha: str, inicio: datetime) -> set[str]:
        reglas = self.problema.reglas
        fin_partido = inicio + timedelta(minutes=partido.minutos_partido)
        fin_turno = inicio + timedelta(minutes=partido.minutos_turno)
        unidades = self.problema.fisicas.get(cancha, frozenset({cancha}))
        mios = set(partido.equipos_definidos)
        companeros: dict[Hashable, str] = {}
        for par in self.problema.pares:
            if par.a in mios:
                companeros[par.b] = par.motivo
            if par.b in mios:
                companeros[par.a] = par.motivo

        encontrados: set[str] = set()
        del_dia = self.por_dia.get(inicio.date(), [])
        partidos_por_equipo: Counter[Hashable] = Counter()
        for otro in del_dia:
            su_cancha, su_inicio, su_fin_partido, su_fin_turno = self.lugar(otro)
            suyos = set(otro.equipos_definidos)
            partidos_por_equipo.update(suyos & mios)
            otras_unidades = self.problema.fisicas.get(su_cancha, frozenset({su_cancha}))
            if unidades & otras_unidades and _se_pisan(inicio, fin_turno, su_inicio, su_fin_turno):
                encontrados.add("cancha")
            if suyos & mios:
                antes, despues = sorted(
                    [(inicio, fin_turno, partido), (su_inicio, su_fin_turno, otro)],
                    key=lambda t: t[0],
                )
                libre = (despues[0] - antes[1]).total_seconds() / 60
                if libre < reglas.turnos_libres_mismo_dia * antes[2].minutos_turno:
                    encontrados.add("equipo")
            for equipo in suyos:
                motivo = companeros.get(equipo)
                if motivo is None:
                    continue
                if _se_pisan(inicio, fin_partido, su_inicio, su_fin_partido):
                    encontrados.add("persona")
                    continue
                antes_fin, despues_inicio = (
                    (fin_partido, su_inicio) if inicio < su_inicio else (su_fin_partido, inicio)
                )
                hueco = (despues_inicio - antes_fin).total_seconds() / 60
                if (
                    motivo == "profe"
                    and cancha != su_cancha
                    and hueco < (reglas.profe_minutos_cambio_de_cancha)
                ):
                    encontrados.add("persona")
        if any(n >= reglas.max_partidos_por_dia for n in partidos_por_equipo.values()):
            encontrados.add("equipo")
        for bloqueo in self.problema.bloqueos:
            if bloqueo.equipo in mios and _se_pisan(
                inicio, fin_partido, bloqueo.inicio, bloqueo.fin
            ):
                encontrados.add("bloqueo")
        if self._antes_de_lo_que_espera(partido, inicio) or self._despues_de_lo_que_sigue(
            partido, fin_turno
        ):
            encontrados.add("orden")
        return encontrados

    def _antes_de_lo_que_espera(self, partido: PartidoAProgramar, inicio: datetime) -> bool:
        for otro in self.problema.partidos:
            if otro.id not in self.ubicados or otro.categoria != partido.categoria:
                continue
            espera = (
                partido.fase == "eliminacion"
                and (otro.fase == "grupos" or otro.clave in partido.despues_de)
            ) or (
                partido.fecha is not None
                and otro.fecha is not None
                and otro.fecha < partido.fecha
                and set(otro.equipos_definidos) & set(partido.equipos_definidos)
            )
            if espera and self.lugar(otro)[3] > inicio:
                return True
        return False

    def _despues_de_lo_que_sigue(self, partido: PartidoAProgramar, fin_turno: datetime) -> bool:
        for otro in self.problema.partidos:
            if otro.id not in self.ubicados or otro.categoria != partido.categoria:
                continue
            sigue = (partido.fase == "grupos" and otro.fase == "eliminacion") or (
                partido.fecha is not None
                and otro.fecha is not None
                and otro.fecha > partido.fecha
                and set(otro.equipos_definidos) & set(partido.equipos_definidos)
            )
            if sigue and self.lugar(otro)[1] < fin_turno:
                return True
        return False


def _inicios(problema: Problema, partido: PartidoAProgramar) -> list[datetime]:
    largo = timedelta(minutes=partido.minutos_partido)
    inicios = []
    for desde, hasta in problema.franjas:
        momento = desde
        while momento + largo <= hasta:
            if (
                partido.fase != "eliminacion"
                or not problema.eliminacion_desde
                or (momento >= problema.eliminacion_desde)
            ):
                inicios.append(momento)
            momento += timedelta(minutes=PASO_MIN)
    return inicios


def motivos_sin_ubicar(problema: Problema, resultado: Resultado) -> dict[Hashable, str]:
    calendario = _Calendario(problema, resultado)
    por_clave = {(p.categoria, p.clave): p for p in problema.partidos if p.clave}
    motivos: dict[Hashable, str] = {}
    for id_ in resultado.sin_ubicar:
        partido = calendario.partidos[id_]
        canchas = sorted(partido.canchas & set(problema.fisicas))
        if not canchas:
            motivos[id_] = "No tiene canchas compatibles"
            continue
        faltantes = [
            por_clave[(partido.categoria, clave)]
            for clave in sorted(partido.despues_de)
            if (partido.categoria, clave) in por_clave
            and por_clave[(partido.categoria, clave)].id not in resultado.ubicados
        ]
        if faltantes:
            nombres = " y ".join(f.nombre or f.clave for f in faltantes)
            motivos[id_] = f"Espera a {nombres}, que tampoco tiene lugar"
            continue
        inicios = _inicios(problema, partido)
        if not inicios:
            motivos[id_] = "No entra en ninguna franja" + (
                " desde el fin de semana de la eliminación" if partido.fase == "eliminacion" else ""
            )
            continue
        conteo: Counter[str] = Counter()
        hay_lugar = False
        for inicio in inicios:
            for cancha in canchas:
                encontrados = calendario.problemas(partido, cancha, inicio)
                conteo.update(encontrados)
                hay_lugar = hay_lugar or not encontrados
        if hay_lugar:
            motivos[id_] = "Hay lugar, pero el programador no llegó a ubicarlo en el tiempo dado"
            continue
        principal = conteo.most_common(1)[0][0]
        motivos[id_] = MOTIVOS[principal].format(canchas=" ni ".join(canchas))
    return motivos
