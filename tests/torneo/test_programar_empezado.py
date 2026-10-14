"""B4 (fase 12): volver a programar con el torneo empezado. Datos inventados."""

from datetime import datetime
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Partido, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import (
    programar_torneo,
    resumen_antes_de_programar,
)

AHORA = timezone.make_aware(datetime(2026, 10, 25, 15, 0))  # el domingo 25 a las 15:00


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10
    settings.PROGRAMADOR_TRABAJADORES = 4


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    for nivel in ("avanzado", "inicial"):
        cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel=nivel)
        for i in range(4):
            club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
            Equipo.objects.create(club=club, categoria=cn, nombre=f"{nivel[:3]} {i}")
        generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    return torneo


@pytest.fixture
def empezado(torneo: Torneo, monkeypatch: pytest.MonkeyPatch) -> dict[str, list[Partido]]:
    """El primer fin de semana ya pasó: uno jugado, uno sin resultado y dos suspendidos."""
    monkeypatch.setattr(timezone, "now", lambda: AHORA)
    antes = list(
        Partido.objects.filter(inicio__lt=AHORA, inicio__isnull=False, fase="grupos").order_by(
            "inicio"
        )
    )
    assert len(antes) >= 4, "el torneo de prueba tiene que tener partidos antes de AHORA"
    jugado, sin_resultado, *suspendidos = antes[:4]
    Partido.objects.filter(pk=jugado.pk).update(estado="jugado")
    for p in suspendidos[:2]:
        Partido.objects.filter(pk=p.pk).update(estado="pendiente", cancha=None, inicio=None)
    return {
        "jugado": [jugado],
        "sin_resultado": [sin_resultado],
        "suspendidos": suspendidos[:2],
    }


def lugar(p: Partido) -> tuple[Any, Any]:
    p.refresh_from_db()
    return (p.cancha_id, p.inicio)


@pytest.mark.django_db
def test_nunca_ubica_antes_de_ahora_ni_mueve_lo_que_ya_paso(
    torneo: Torneo, empezado: dict[str, list[Partido]]
) -> None:
    jugado, sin_resultado = empezado["jugado"][0], empezado["sin_resultado"][0]
    fijos = {p.pk: lugar(p) for p in (jugado, sin_resultado)}
    corrida = programar_torneo(torneo)
    for pk, quedo in fijos.items():
        assert lugar(Partido.objects.get(pk=pk)) == quedo
    for p in empezado["suspendidos"]:
        p.refresh_from_db()
        assert p.inicio is not None and p.inicio >= AHORA  # desde ahora, nunca antes
    # B4: avisa que al que ya pasó de hora le falta el resultado.
    pasados = Partido.objects.filter(inicio__lte=AHORA).exclude(estado="jugado").count()
    assert pasados >= 1
    assert len(corrida.resultado["sin_resultado"]) == pasados


@pytest.mark.django_db
def test_ubicar_solo_lo_que_falta_deja_todo_lo_demas_donde_esta(
    torneo: Torneo, empezado: dict[str, list[Partido]]
) -> None:
    antes = {
        p.pk: lugar(p)
        for p in Partido.objects.filter(inicio__isnull=False)
        if p.pk not in {s.pk for s in empezado["suspendidos"]}
    }
    programar_torneo(torneo, solo_lo_que_falta=True)
    for pk, quedo in antes.items():
        assert lugar(Partido.objects.get(pk=pk)) == quedo
    for p in empezado["suspendidos"]:
        p.refresh_from_db()
        assert p.inicio is not None and p.inicio >= AHORA


@pytest.mark.django_db
def test_el_resumen_cuenta_lo_que_no_se_mueve_y_lo_que_si(
    torneo: Torneo, empezado: dict[str, list[Partido]]
) -> None:
    resumen = resumen_antes_de_programar(torneo)
    assert resumen.jugados == 1
    assert len(resumen.sin_resultado) >= 1
    assert resumen.sin_lugar == 2
    assert resumen.futuros > 0
    assert resumen.hay_publicados


@pytest.mark.django_db
def test_la_pantalla_pide_confirmar_y_dice_cuantos_se_mueven(
    client: Client, torneo: Torneo, empezado: dict[str, list[Partido]]
) -> None:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    url = f"/torneos/{torneo.pk}/programar/"
    html = client.get(url).content.decode()
    assert "Ubicar solo lo que falta" in html
    assert "les falta el resultado" in html
    antes = {p.pk: lugar(p) for p in Partido.objects.filter(inicio__isnull=False)}
    respuesta = client.post(url, {"modo": "todo"})
    assert "¿Estás seguro?" in respuesta.content.decode()
    assert "programados" in respuesta.content.decode()
    assert {p.pk: lugar(p) for p in Partido.objects.filter(inicio__isnull=False)} == antes
    # El atajo "solo lo que falta" no mueve nada que ya tiene lugar, y no pide confirmar.
    respuesta = client.post(url, {"modo": "faltan"})
    assert "¿Estás seguro?" not in respuesta.content.decode()
