"""T5.3: propuestas en pantalla, aplicar una y el historial de cambios. Datos inventados."""

from datetime import timedelta
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Bloqueo, Cambio, CategoriaNivel, Club, Corrida, Equipo, Partido
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo, verificar_torneo


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10
    settings.PROGRAMADOR_TRABAJADORES = 4


@pytest.fixture
def bloqueo() -> Bloqueo:
    """Un torneo chico programado y un bloqueo encima de un partido programado."""
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(6):
        club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
        Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}")
    generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    victima = Partido.objects.filter(fase="grupos", inicio__isnull=False).order_by("inicio").first()
    assert victima is not None and victima.inicio is not None and victima.local is not None
    nuevo = Bloqueo.objects.create(
        torneo=torneo,
        inicio=victima.inicio - timedelta(minutes=10),
        fin=victima.inicio + timedelta(hours=1),
    )
    nuevo.equipos.add(victima.local)
    return nuevo


def entrar(client: Client, grupo: str) -> Client:
    usuario = User.objects.create_user("seba" if grupo == ORGANIZACION else "mesa", password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


@pytest.mark.django_db
def test_un_bloqueo_da_propuestas_ordenadas_y_aplicar_deja_todo_sin_choques(
    client: Client, bloqueo: Bloqueo
) -> None:
    org = entrar(client, ORGANIZACION)
    respuesta = org.post(f"/bloqueos/{bloqueo.pk}/propuestas/")
    corrida = Corrida.objects.get(tipo=Corrida.Tipo.REPROGRAMAR)
    assert respuesta["Location"] == f"/corridas/{corrida.pk}/propuestas/"
    propuestas = corrida.resultado["propuestas"]
    assert 2 <= len(propuestas) <= 3
    cantidades = [len(p) for p in propuestas]
    assert cantidades == sorted(cantidades)

    html = org.get(respuesta["Location"]).content.decode()
    assert "Recomendada" in html
    assert f"Mover {cantidades[0]} partido" in html

    assert verificar_torneo(bloqueo.torneo) != {}  # el bloqueo choca
    org.post(f"/corridas/{corrida.pk}/aplicar/0/")
    assert verificar_torneo(bloqueo.torneo) == {}
    assert Cambio.objects.count() == cantidades[0]
    cambio = Cambio.objects.select_related("usuario").first()
    assert cambio is not None and cambio.usuario is not None
    assert cambio.usuario.username == "seba"
    assert cambio.motivo == bloqueo.motivo


@pytest.mark.django_db
def test_una_propuesta_vieja_no_se_aplica(client: Client, bloqueo: Bloqueo) -> None:
    org = entrar(client, ORGANIZACION)
    org.post(f"/bloqueos/{bloqueo.pk}/propuestas/")
    corrida = Corrida.objects.get(tipo=Corrida.Tipo.REPROGRAMAR)
    otro = Partido.objects.filter(inicio__isnull=False).order_by("-inicio").first()
    assert otro is not None and otro.inicio is not None
    Partido.objects.filter(pk=otro.pk).update(inicio=otro.inicio + timedelta(minutes=5))
    respuesta = org.post(f"/corridas/{corrida.pk}/aplicar/0/", follow=True)
    assert "El calendario cambió" in respuesta.content.decode()
    assert not Cambio.objects.exists()


@pytest.mark.django_db
def test_el_historial_se_ve_en_mas(client: Client, bloqueo: Bloqueo) -> None:
    org = entrar(client, ORGANIZACION)
    org.post(f"/bloqueos/{bloqueo.pk}/propuestas/")
    corrida = Corrida.objects.get(tipo=Corrida.Tipo.REPROGRAMAR)
    org.post(f"/corridas/{corrida.pk}/aplicar/0/")
    html = org.get("/mas/").content.decode()
    assert "Cambios recientes" in html
    assert "→" in html


@pytest.mark.django_db
def test_la_mesa_no_reprograma(client: Client, bloqueo: Bloqueo) -> None:
    mesa = entrar(client, MESA)
    assert mesa.post(f"/bloqueos/{bloqueo.pk}/propuestas/").status_code == 403


@pytest.mark.django_db
def test_verificar_torneo_cuenta_choques_por_tipo(bloqueo: Bloqueo) -> None:
    assert verificar_torneo(bloqueo.torneo) == {"bloqueo": 1}
