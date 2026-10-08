"""Hallazgos de la revisión de cierre de la fase 4 (ver PROGRESO.md). Datos inventados."""

import pytest
from django.conf import settings
from django.db import connection
from django.test.utils import CaptureQueriesContext

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Partido, Torneo
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import problema_del_torneo


def consultas_para(categorias: list[str]) -> int:
    torneo = Torneo.objects.first() or cargar_configuracion(
        cargar_config(settings.PLANTILLA_TORNEO)
    )
    for nombre in categorias:
        cn = torneo.categorias.get(categoria=nombre, nivel="avanzado")
        for i in range(6):
            club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
            Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}")
        generar_fixture(cn, semilla=1)
    partidos = list(
        Partido.objects.filter(categoria__torneo=torneo).select_related(
            "categoria__torneo", "cancha", "local", "visitante"
        )
    )
    with CaptureQueriesContext(connection) as consultas:
        problema_del_torneo(torneo, partidos)
    return len(consultas)


@pytest.mark.django_db
def test_armar_el_problema_no_consulta_por_partido() -> None:
    con_una = consultas_para(["Sub 9"])  # 14 partidos
    con_tres = consultas_para(["Sub 10", "Sub 11"])  # 42 partidos en total
    assert con_tres - con_una <= 4, (con_una, con_tres)
