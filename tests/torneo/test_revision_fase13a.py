"""Revisión de cierre de las fases 11 y 12 y del bloque A de la fase 13. Datos inventados."""

import pytest
from django.conf import settings

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Partido
from torneo.servicios import partido as servicio
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.partido import NoSePuede


@pytest.fixture
def partido() -> Partido:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
    generar_fixture(cn, semilla=1)
    return Partido.objects.filter(fase=Partido.Fase.GRUPOS).first()  # type: ignore[return-value]


@pytest.mark.django_db
def test_no_se_da_wo_a_un_partido_empezado(partido: Partido) -> None:
    servicio.empezar(partido, None)
    with pytest.raises(NoSePuede, match="ya empezó"):
        servicio.wo(partido, "local", None)
    partido.refresh_from_db()
    assert partido.estado == Partido.Estado.EN_JUEGO and partido.no_se_presento == ""


@pytest.mark.django_db
def test_no_se_da_wo_a_un_partido_terminado(partido: Partido) -> None:
    servicio.empezar(partido, None)
    servicio.terminar(partido, None)
    with pytest.raises(NoSePuede):
        servicio.wo(partido, "visitante", None)


@pytest.mark.django_db
def test_el_wo_sigue_andando_antes_de_empezar(partido: Partido) -> None:
    servicio.wo(partido, "local", None)
    partido.refresh_from_db()
    assert (partido.estado, partido.no_se_presento) == (Partido.Estado.JUGADO, "local")
