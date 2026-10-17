"""T13.44: los motivos de los choques dicen el nombre del equipo y de la categoría.

Las propuestas decían "Choca: 21: Partido de la ACF" (el id del equipo) y los demás motivos del
verificador, lo mismo; los de categoría, "12 no juega en C3". Datos inventados.
"""

from datetime import timedelta
from typing import Any

import pytest
from django.conf import settings

from dominio.config import cargar_config
from torneo.models import Bloqueo, CategoriaNivel, Club, Equipo, Partido, Torneo
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import (
    calendario_actual,
    choques_del_calendario,
    partidos_del_torneo,
    problema_del_torneo,
    programar_torneo,
)
from torneo.servicios.reprogramar import calcular_propuestas


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for nombre in ("River", "Bolívar", "Tigre", "Wilstermann"):
        Equipo.objects.create(club=Club.objects.create(nombre=nombre), categoria=cn, nombre=nombre)
    generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    return torneo


@pytest.mark.django_db
def test_el_por_que_de_las_propuestas_dice_el_nombre_del_equipo(torneo: Torneo) -> None:
    partido = Partido.objects.filter(inicio__isnull=False).order_by("inicio").first()
    assert partido is not None and partido.inicio is not None and partido.local is not None
    bloqueo = Bloqueo.objects.create(
        torneo=torneo,
        inicio=partido.inicio - timedelta(hours=1),
        fin=partido.inicio + timedelta(hours=1),
        motivo="Partido de la ACF",
    )
    bloqueo.equipos.set([partido.local])
    corrida = calcular_propuestas(bloqueo)
    motivos = {m["motivo"] for p in corrida.resultado["propuestas"] for m in p}
    assert f"Choca: {partido.local.nombre}: Partido de la ACF" in motivos


@pytest.mark.django_db
def test_un_motivo_de_categoria_dice_su_nombre(torneo: Torneo) -> None:
    partidos = partidos_del_torneo(torneo)
    calendario = calendario_actual(partidos)
    uno = partidos[0]
    calendario[uno.pk] = ("C1A", calendario[uno.pk][1])  # Sub 9 Avanzado no juega en una mitad
    motivos = [
        m
        for c in choques_del_calendario(problema_del_torneo(torneo, partidos), calendario)
        for m in c.motivos
    ]
    assert "Sub 9 Avanzado no juega en C1A" in motivos
