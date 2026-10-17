"""T13.42: "Ver propuestas" para un bloqueo con partidos sin lugar en el calendario.

Solo se mueve lo que choca (no se aprovecha para ubicar lo que estaba sin lugar). Si el solver no
termina, la pantalla dice "No terminé de buscar a tiempo", no "no hay forma"; y sin propuestas,
ofrece igual los horarios libres de Mover (T13.17) para el partido que choca. Datos inventados.
"""

from datetime import timedelta
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from dominio.programador.reprogramar import Busqueda
from torneo.models import Bloqueo, CategoriaNivel, Club, Corrida, Equipo, Partido, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios import reprogramar as servicio
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo
from torneo.servicios.reprogramar import calcular_propuestas


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    for categoria in ("Sub 9", "Sub 10"):
        cn: CategoriaNivel = torneo.categorias.get(categoria=categoria, nivel="avanzado")
        for i in range(4):
            Equipo.objects.create(
                club=Club.objects.create(nombre=f"Club {categoria} {i}"),
                categoria=cn,
                nombre=f"Equipo {i}",
            )
        generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    # Como la demo con 0,1 CPU: lo de Sub 10 quedó sin lugar.
    Partido.objects.filter(categoria__categoria="Sub 10").update(
        inicio=None, cancha=None, estado=Partido.Estado.PENDIENTE
    )
    return torneo


@pytest.fixture
def bloqueo(torneo: Torneo) -> Bloqueo:
    partido = (
        Partido.objects.filter(categoria__categoria="Sub 9", inicio__isnull=False)
        .order_by("inicio")
        .first()
    )
    assert partido is not None and partido.inicio is not None and partido.local is not None
    bloqueo = Bloqueo.objects.create(
        torneo=torneo,
        inicio=partido.inicio - timedelta(hours=1),
        fin=partido.inicio + timedelta(hours=1),
        motivo="Partido de la ACF",
    )
    bloqueo.equipos.set([partido.local])
    return bloqueo


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


@pytest.mark.django_db
def test_las_propuestas_de_un_bloqueo_no_ubican_lo_que_estaba_sin_lugar(bloqueo: Bloqueo) -> None:
    corrida = calcular_propuestas(bloqueo)
    sin_lugar = set(
        Partido.objects.filter(categoria__categoria="Sub 10").values_list("pk", flat=True)
    )
    assert corrida.resultado["propuestas"]
    assert corrida.resultado["sin_terminar"] is False
    for propuesta in corrida.resultado["propuestas"]:
        assert all(m["antes"] is not None for m in propuesta)
        assert not {m["partido"] for m in propuesta} & sin_lugar


@pytest.mark.django_db
def test_volver_a_calcular_tampoco(org: Client, bloqueo: Bloqueo) -> None:
    corrida = calcular_propuestas(bloqueo)
    org.post(f"/corridas/{corrida.pk}/recalcular/", {})
    otra = Corrida.objects.filter(tipo=Corrida.Tipo.REPROGRAMAR).latest("pk")
    assert otra.pk != corrida.pk
    for propuesta in otra.resultado["propuestas"]:
        assert all(m["antes"] is not None for m in propuesta)


def _sin_terminar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        servicio, "buscar_propuestas", lambda *a, **k: Busqueda(propuestas=[], sin_terminar=True)
    )


@pytest.mark.django_db
def test_si_no_termino_a_tiempo_lo_dice(
    org: Client, bloqueo: Bloqueo, monkeypatch: pytest.MonkeyPatch
) -> None:
    _sin_terminar(monkeypatch)
    corrida = calcular_propuestas(bloqueo)
    assert corrida.resultado["sin_terminar"] is True
    html = org.get(f"/corridas/{corrida.pk}/propuestas/").content.decode()
    assert "No terminé de buscar a tiempo" in html
    assert "no hay forma" not in html


@pytest.mark.django_db
def test_sin_propuestas_ofrece_los_horarios_libres_de_mover(
    org: Client, bloqueo: Bloqueo, monkeypatch: pytest.MonkeyPatch
) -> None:
    _sin_terminar(monkeypatch)
    corrida = calcular_propuestas(bloqueo)
    html = org.get(f"/corridas/{corrida.pk}/propuestas/").content.decode()
    partido = next(p for p, _ in servicio.afectados_por(bloqueo))
    assert "Horarios libres" in html
    assert html.count(f'action="/partidos/{partido.pk}/mover/"') >= 3
    # Ninguno cae en el horario del bloqueo.
    assert partido.inicio is not None
    for hora in (bloqueo.inicio + timedelta(minutes=m) for m in range(0, 120, 5)):
        local = timezone.localtime(hora)
        assert (
            f'name="dia" value="{local.date().isoformat()}"><input type="hidden" '
            f'name="hora" value="{local:%H:%M}">'
        ) not in html


@pytest.mark.django_db
def test_con_propuestas_no_muestra_los_horarios_libres(org: Client, bloqueo: Bloqueo) -> None:
    corrida = calcular_propuestas(bloqueo)
    html = org.get(f"/corridas/{corrida.pk}/propuestas/").content.decode()
    assert corrida.resultado["propuestas"] and "Horarios libres" not in html
