"""T13.35: si el solver no encuentra ninguna solución en el tiempo, el calendario queda como
estaba y la pantalla lo dice. Nunca "0 de 223, sin choques" en verde."""

from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from dominio.programador.modelo import Problema, Resultado
from torneo.models import CategoriaNivel, Club, Corrida, Equipo, Partido, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios import programador
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo, trabajadores_para_la_cpu


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10
    settings.PROGRAMADOR_TRABAJADORES = 4


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
        Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}")
    generar_fixture(cn, semilla=1)
    return torneo


def _sin_solucion(problema: Problema, **_: Any) -> Resultado:
    return Resultado(sin_ubicar=[p.id for p in problema.partidos], estado="UNKNOWN")


def _lugares(torneo: Torneo) -> dict[int, tuple[Any, Any, str]]:
    return {
        p.pk: (p.cancha_id, p.inicio, p.estado)
        for p in Partido.objects.filter(categoria__torneo=torneo)
    }


@pytest.mark.django_db
def test_sin_solucion_el_calendario_queda_como_estaba(
    torneo: Torneo, monkeypatch: pytest.MonkeyPatch
) -> None:
    programar_torneo(torneo)
    antes = _lugares(torneo)
    assert all(cancha is not None for cancha, _, _ in antes.values())

    monkeypatch.setattr(programador, "programar", _sin_solucion)
    corrida = programar_torneo(torneo)

    assert _lugares(torneo) == antes
    assert corrida.estado == Corrida.Estado.TERMINADA
    assert corrida.resultado["sin_solucion"] is True
    assert corrida.resultado["estado_solver"] == "UNKNOWN"


@pytest.mark.django_db
def test_volver_a_programar_le_da_al_solver_el_calendario_actual(
    torneo: Torneo, monkeypatch: pytest.MonkeyPatch
) -> None:
    programar_torneo(torneo)
    antes = {
        p.pk: (p.cancha.codigo, programador.hora_local(p.inicio))
        for p in Partido.objects.filter(categoria__torneo=torneo).select_related("cancha")
        if p.cancha and p.inicio
    }
    vistos: list[Problema] = []

    def espiar(problema: Problema, **_: Any) -> Resultado:
        vistos.append(problema)
        return _sin_solucion(problema)

    monkeypatch.setattr(programador, "programar", espiar)
    programar_torneo(torneo)

    (problema,) = vistos
    assert {p.id: p.pista for p in problema.partidos} == antes


def test_con_menos_de_una_cpu_usa_dos_trabajadores(tmp_path: Path) -> None:
    """Medido con 0,1 CPU (PROGRESO, H9): 8 trabajadores no encontraron nada en 60 s, 2
    ubicaron 138 de 223."""
    cpu_max = tmp_path / "cpu.max"
    cpu_max.write_text("10000 100000\n")
    assert trabajadores_para_la_cpu(8, cpu_max) == 2
    cpu_max.write_text("max 100000\n")
    assert trabajadores_para_la_cpu(8, cpu_max) == 8
    cpu_max.write_text("200000 100000\n")
    assert trabajadores_para_la_cpu(4, cpu_max) == 4
    assert trabajadores_para_la_cpu(1, cpu_max) == 1
    assert trabajadores_para_la_cpu(8, tmp_path / "no-existe") == 8


def _pantalla(client: Client, torneo: Torneo, resultado: dict[str, Any]) -> str:
    Corrida.objects.create(
        torneo=torneo, estado=Corrida.Estado.TERMINADA, resultado=resultado, duracion=61
    )
    usuario = User.objects.create_user("orga", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client.get(f"/torneos/{torneo.pk}/programar/").content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "resultado",
    [
        {"sin_solucion": True, "estado_solver": "UNKNOWN", "total": 223, "ubicados": 0},
        # Una corrida de antes de T13.35, sin la marca: 0 ubicados también es "sin solución".
        {"estado_solver": "UNKNOWN", "total": 223, "ubicados": 0, "choques": {}},
    ],
)
def test_sin_solucion_la_pantalla_lo_dice_y_sugiere_que_hacer(
    client: Client, torneo: Torneo, resultado: dict[str, Any]
) -> None:
    html = _pantalla(client, torneo, resultado)
    assert "sin choques" not in html
    assert "alerta bien" not in html
    assert "No encontró una solución en el tiempo" in html
    assert "El calendario quedó como estaba" in html
    assert "más tiempo" in html and "más CPU" in html


@pytest.mark.django_db
def test_si_quedan_partidos_sin_lugar_no_es_verde(client: Client, torneo: Torneo) -> None:
    html = _pantalla(
        client, torneo, {"estado_solver": "FEASIBLE", "total": 223, "ubicados": 216, "choques": {}}
    )
    assert "216 de 223 partidos programados" in html
    assert "alerta aviso" in html and "alerta bien" not in html


@pytest.mark.django_db
def test_con_todo_ubicado_sigue_en_verde(client: Client, torneo: Torneo) -> None:
    html = _pantalla(
        client, torneo, {"estado_solver": "FEASIBLE", "total": 223, "ubicados": 223, "choques": {}}
    )
    assert "223 de 223 partidos programados, sin choques" in html and "alerta bien" in html


@pytest.mark.django_db
def test_con_poca_cpu_el_servicio_pide_una_sola_pasada(
    torneo: Torneo, monkeypatch: pytest.MonkeyPatch
) -> None:
    pedidos: list[dict[str, Any]] = []

    def espiar(problema: Problema, **opciones: Any) -> Resultado:
        pedidos.append(opciones)
        return _sin_solucion(problema)

    monkeypatch.setattr(programador, "programar", espiar)
    monkeypatch.setattr(programador, "poca_cpu", lambda: True)
    corrida = programar_torneo(torneo)
    assert pedidos[0]["una_pasada"] is True
    assert pedidos[0]["trabajadores"] == 2
    assert corrida.parametros["poca_cpu"] is True


@pytest.mark.django_db
def test_con_solucion_y_nada_ubicado_no_dice_que_no_encontro(
    client: Client, torneo: Torneo
) -> None:
    """Si nada entra (por ejemplo, sin franjas), el solver sí terminó: no es "sin solución"."""
    html = _pantalla(
        client,
        torneo,
        {"estado_solver": "OPTIMAL", "total": 4, "ubicados": 0, "choques": {}, "sin_ubicar": []},
    )
    assert "No encontró una solución en el tiempo" not in html
    assert "0 de 4 partidos programados" in html
