"""Hallazgos de la revisión de cierre de la fase 3 (ver PROGRESO.md)."""

import pytest
from django.conf import settings

from dominio.config import cargar_config
from torneo.models import Club, Equipo
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.views.fixture import datos_del_fixture


@pytest.mark.django_db
def test_el_fixture_no_hace_consultas_por_serie(django_assert_max_num_queries: object) -> None:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    categoria = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(10):
        club = Club.objects.create(nombre=f"Club {i}")
        Equipo.objects.create(club=club, categoria=categoria, nombre=f"Equipo {i}")
    generar_fixture(categoria)
    with django_assert_max_num_queries(6):  # type: ignore[operator]
        datos = datos_del_fixture(categoria)
    assert [len(s["equipos"]) for s in datos["series"]] == [5, 5]
