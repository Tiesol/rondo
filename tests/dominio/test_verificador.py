"""VER-01 y PRO-01 a PRO-07: verificador de choques, con la prueba de 2023 (6.3 y 6.4)."""

import csv
import json
import re
from collections import Counter
from datetime import date, datetime, time, timedelta
from itertools import combinations
from pathlib import Path
from typing import Any, Literal

import pytest

from dominio.config import Reglas, cargar_config
from dominio.verificador import (
    Bloqueo,
    Escenario,
    ParDeEquipos,
    PartidoAgendado,
    verificar,
)

RAIZ = Path(__file__).resolve().parents[2]

# ---------- Prueba 2023 ----------

# Las categorías de 2023 pasadas a las de 2026 (igual que la demo, datos/demo/equipos.json).
CATEGORIA_2026 = {
    "Sub 5": ("Sub 5", "unico"),
    "Sub 6": ("Sub 6", "unico"),
    "Sub 7": ("Sub 7", "avanzado"),
    "Sub 8 Inicial": ("Sub 8", "inicial"),
    "Sub 8 Avanzado": ("Sub 8", "avanzado"),
    "Sub 9 Inicial": ("Sub 9", "inicial"),
    "Sub 9 Avanzado": ("Sub 9", "avanzado"),
    "Sub 10 Inicial": ("Sub 10", "inicial"),
    "Sub 10 Avanzado": ("Sub 10", "avanzado"),
    "Sub 11 Inicial": ("Sub 11", "inicial"),
    "Sub 11 Avanzado": ("Sub 11", "avanzado"),
    "Sub 12": ("Sub 12", "avanzado"),
    "Sub 13": ("Sub 13", "avanzado"),
    "Sub 15": ("Sub 15", "avanzado"),
}
# 6.1: las canchas de 2023 (H3: con las de 2026, Sub 10 Avanzado daría choques de compatibilidad).
CANCHAS_2023 = {
    "Sub 5|unico": {"C1A", "C1B"},
    "Sub 6|unico": {"C1A", "C1B"},
    "Sub 9|inicial": {"C1"},
    "Sub 9|avanzado": {"C1"},
    "Sub 11|avanzado": {"C1"},
    "Sub 7|avanzado": {"C2"},
    "Sub 8|inicial": {"C2"},
    "Sub 8|avanzado": {"C2"},
    "Sub 10|inicial": {"C2"},
    "Sub 10|avanzado": {"C2"},
    "Sub 11|inicial": {"C2"},
    "Sub 12|avanzado": {"C3"},
    "Sub 13|avanzado": {"C3"},
    "Sub 15|avanzado": {"C3"},
}
FISICAS = {"C1": {"C1A", "C1B"}, "C1A": {"C1A"}, "C1B": {"C1B"}, "C2": {"C2"}, "C3": {"C3"}}


def escenario_2023() -> tuple[list[PartidoAgendado], Escenario]:
    config = cargar_config(RAIZ / "datos" / "config" / "jmp_cup_2026.json")
    partidos = []
    with (RAIZ / "datos" / "pruebas" / "calendario_2023.csv").open() as archivo:
        for numero, fila in enumerate(csv.DictReader(archivo)):
            categoria, nivel = CATEGORIA_2026[re.sub(r" [AB]$", "", fila["categoria"])]
            minutos = config.categoria(categoria).niveles[nivel]  # type: ignore[index]
            clave = f"{categoria}|{nivel}"
            inicio = datetime.combine(
                date.fromisoformat(fila["fecha"]), time.fromisoformat(fila["inicio"])
            )
            partidos.append(
                PartidoAgendado(
                    id=numero,
                    categoria=clave,
                    equipos=(f"{fila['local']}|{clave}", f"{fila['visitante']}|{clave}"),
                    cancha=fila["cancha"],
                    inicio=inicio,
                    minutos_partido=config.minutos_partido(minutos),
                    minutos_turno=config.minutos_turno(minutos),
                )
            )

    grupos = json.loads((RAIZ / "datos" / "demo" / "equipos.json").read_text())
    # 6.4 completo: la demo omite un par de Crack FC (R35), pero la prueba usa los datos de 2023.
    profes = [*grupos["profes_compartidos"]]
    profes.append({"veces": 1, "equipos": ["Crack FC|Sub 7|avanzado", "Crack FC|Sub 8|avanzado"]})
    motivos: tuple[tuple[Literal["profe", "jugador"], list[Any]], ...] = (
        ("profe", profes),
        ("jugador", grupos["jugadores_compartidos"]),
    )
    pares = [
        ParDeEquipos(a, b, motivo)
        for motivo, lista in motivos
        for grupo in lista
        for _ in range(grupo["veces"])
        for a, b in combinations(grupo["equipos"], 2)
    ]
    franjas = [(datetime(2023, 10, d, 8), datetime(2023, 10, d, 16)) for d in (14, 15)]
    escenario = Escenario(
        fisicas={c: frozenset(u) for c, u in FISICAS.items()},
        compatibilidad={k: frozenset(v) for k, v in CANCHAS_2023.items()},
        franjas=tuple(franjas),
        pares=tuple(pares),
        bloqueos=(),
        reglas=Reglas(),
    )
    return partidos, escenario


def test_ver_01_prueba_2023_por_tipo() -> None:
    partidos, escenario = escenario_2023()
    choques = verificar(partidos, escenario)
    por_tipo = Counter(c.tipo for c in choques)
    assert por_tipo["persona"] == 2
    assert por_tipo["cancha"] == 3
    assert por_tipo["compatibilidad"] == 0
    assert por_tipo["equipo"] == 0
    assert por_tipo["franja"] == 0


def test_ver_01_los_dos_de_personas_son_los_de_river_plate() -> None:
    partidos, escenario = escenario_2023()
    por_id = {p.id: p for p in partidos}
    personas = [c for c in verificar(partidos, escenario) if c.tipo == "persona"]
    descripciones = sorted(
        tuple(sorted((por_id[i].inicio.strftime("%d %H:%M"), por_id[i].cancha) for i in c.partidos))
        for c in personas
    )
    assert descripciones == [
        (("14 09:20", "C1"), ("14 10:00", "C3")),
        (("15 09:20", "C1A"), ("15 09:40", "C2")),
    ]
    for choque in personas:
        for i in choque.partidos:
            assert any("River Plate" in str(e) for e in por_id[i].equipos)
    domingo = next(c for c in personas if por_id[c.partidos[0]].inicio.day == 15)
    assert {"profe", "jugador"} <= {m.split(":")[0] for m in domingo.motivos}


def test_ver_01_los_tres_de_cancha() -> None:
    partidos, escenario = escenario_2023()
    por_id = {p.id: p for p in partidos}
    cancha = [c for c in verificar(partidos, escenario) if c.tipo == "cancha"]
    canchas = sorted(tuple(sorted(por_id[i].cancha for i in c.partidos)) for c in cancha)
    assert canchas == [("C1", "C1A"), ("C1", "C1B"), ("C3", "C3")]


def test_con_las_canchas_de_2026_aparecen_choques_de_compatibilidad() -> None:
    """H3: Sub 10 Avanzado (F8) jugó en C2 en 2023; en 2026, F8 va solo en C1."""
    partidos, escenario = escenario_2023()
    compat = dict(escenario.compatibilidad) | {"Sub 10|avanzado": frozenset({"C1"})}
    otra = Escenario(**{**escenario.__dict__, "compatibilidad": compat})
    assert Counter(c.tipo for c in verificar(partidos, otra))["compatibilidad"] == 2


# ---------- Casos mínimos por tipo ----------

SABADO = date(2026, 10, 24)


def partido(
    id: int,
    hora: str,
    cancha: str = "C2",
    equipos: tuple[str | None, str | None] = ("A", "B"),
    turno: int = 50,
    categoria: str = "Sub 9|inicial",
) -> PartidoAgendado:
    return PartidoAgendado(
        id=id,
        categoria=categoria,
        equipos=equipos,
        cancha=cancha,
        inicio=datetime.combine(SABADO, time.fromisoformat(hora)),
        minutos_partido=turno - 5,
        minutos_turno=turno,
    )


def escenario(**cambios: object) -> Escenario:
    base = {
        "fisicas": {c: frozenset(u) for c, u in FISICAS.items()},
        "compatibilidad": {"Sub 9|inicial": frozenset({"C1", "C2", "C3"})},
        "franjas": ((datetime.combine(SABADO, time(8)), datetime.combine(SABADO, time(16))),),
        "pares": (),
        "bloqueos": (),
        "reglas": Reglas(),
    }
    return Escenario(**(base | cambios))  # type: ignore[arg-type]


def tipos(partidos: list[PartidoAgendado], esc: Escenario) -> list[str]:
    return sorted(c.tipo for c in verificar(partidos, esc))


def test_pro_01_dos_partidos_en_la_misma_cancha_a_la_vez() -> None:
    assert tipos([partido(1, "09:00"), partido(2, "09:30", equipos=("C", "D"))], escenario()) == [
        "cancha"
    ]


def test_pro_01_seguidos_en_la_misma_cancha_no_chocan() -> None:
    assert tipos([partido(1, "09:00"), partido(2, "09:50", equipos=("C", "D"))], escenario()) == []


def test_pro_02_cancha_no_compatible() -> None:
    choques = verificar([partido(1, "09:00", cancha="C1A")], escenario())
    assert [(c.tipo, c.partidos) for c in choques] == [("compatibilidad", (1,))]


def test_pro_03_fuera_de_la_franja_y_el_cambio_puede_quedar_afuera() -> None:
    assert tipos([partido(1, "15:20")], escenario()) == ["franja"]  # termina a las 16:05
    assert tipos([partido(1, "15:15")], escenario()) == []  # termina 16:00; el cambio, afuera


def test_pro_04_un_equipo_sin_turno_libre_en_el_dia() -> None:
    juntos = [partido(1, "09:00"), partido(2, "09:50", cancha="C3", equipos=("A", "C"))]
    assert tipos(juntos, escenario()) == ["equipo"]
    con_uno_libre = [partido(1, "09:00"), partido(2, "10:40", cancha="C3", equipos=("A", "C"))]
    assert tipos(con_uno_libre, escenario()) == []


def test_pro_04_mas_partidos_por_dia_que_el_maximo() -> None:
    tres = [
        partido(1, "08:00"),
        partido(2, "09:40", equipos=("A", "C")),
        partido(3, "11:20", equipos=("A", "D")),
    ]
    choques = verificar(tres, escenario())
    assert [(c.tipo, c.partidos) for c in choques] == [("equipo", (1, 2, 3))]


def test_pro_05_un_profe_que_cambia_de_cancha_necesita_margen() -> None:
    pares = (ParDeEquipos("A", "C", "profe"),)
    cerca = [partido(1, "09:00"), partido(2, "09:50", cancha="C3", equipos=("C", "D"))]
    assert tipos(cerca, escenario(pares=pares)) == ["persona"]
    misma_cancha = [partido(1, "09:00"), partido(2, "09:50", equipos=("C", "D"))]
    assert tipos(misma_cancha, escenario(pares=pares)) == []
    lejos = [partido(1, "09:00"), partido(2, "10:00", cancha="C3", equipos=("C", "D"))]
    assert tipos(lejos, escenario(pares=pares)) == []


def test_pro_06_un_jugador_compartido_solo_pide_que_no_se_pisen() -> None:
    pares = (ParDeEquipos("A", "C", "jugador"),)
    pegados = [partido(1, "09:00"), partido(2, "09:50", cancha="C3", equipos=("C", "D"))]
    assert tipos(pegados, escenario(pares=pares)) == []
    a_la_vez = [partido(1, "09:00"), partido(2, "09:30", cancha="C3", equipos=("C", "D"))]
    assert tipos(a_la_vez, escenario(pares=pares)) == ["persona"]


def test_pro_07_bloqueo_de_la_acf() -> None:
    bloqueo = Bloqueo(
        "A", datetime.combine(SABADO, time(10)), datetime.combine(SABADO, time(12)), "ACF"
    )
    assert tipos([partido(1, "09:30")], escenario(bloqueos=(bloqueo,))) == ["bloqueo"]
    assert tipos([partido(1, "08:00")], escenario(bloqueos=(bloqueo,))) == []


def test_ver_01_un_par_con_varios_motivos_es_un_solo_choque() -> None:
    pares = (
        ParDeEquipos("A", "C", "profe"),
        ParDeEquipos("A", "C", "profe"),
        ParDeEquipos("A", "C", "jugador"),
    )
    juntos = [partido(1, "09:00"), partido(2, "09:00", cancha="C3", equipos=("C", "D"))]
    choques = verificar(juntos, escenario(pares=pares))
    assert len(choques) == 1
    assert len(choques[0].motivos) == 3


def test_los_partidos_por_definir_no_chocan_por_equipo() -> None:
    sin_equipos = [
        partido(1, "09:00", equipos=(None, None)),
        partido(2, "09:00", cancha="C3", equipos=(None, None)),
    ]
    assert tipos(sin_equipos, escenario()) == []


@pytest.mark.parametrize("hora", ["07:59", "15:20"])
def test_pro_03_los_bordes_de_la_franja(hora: str) -> None:
    assert tipos([partido(1, hora)], escenario()) == ["franja"]


def test_un_dia_sin_partidos_no_hace_nada() -> None:
    assert verificar([], escenario()) == []


def test_timedelta_de_referencia() -> None:
    assert timedelta(minutes=50) == partido(1, "09:00").fin_turno - partido(1, "09:00").inicio
