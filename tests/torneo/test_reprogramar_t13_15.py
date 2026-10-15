"""T13.15: "Reprogramar" a la vista, desde la ficha del partido y el calendario del día.

Pide el motivo (ACF o decisión de la organización: la convocatoria no atiende pedidos
particulares) y quién no puede, y lleva a las propuestas. También lleva a mover a mano o
intercambiar. La pantalla de la ACF pasa a llamarse "Un equipo no puede jugar". Datos inventados.
"""

from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import Bloqueo, CategoriaNivel, Club, Corrida, Equipo, Partido, Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
    generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    return torneo


@pytest.fixture
def partido(torneo: Torneo) -> Partido:
    p = Partido.objects.filter(inicio__isnull=False).order_by("inicio").first()
    assert p is not None
    return p


def entrar(client: Client, rol: str) -> Client:
    usuario = User.objects.create_user(rol[:4], password="x")
    usuario.groups.add(Group.objects.get(name=rol))
    client.force_login(usuario)
    return client


@pytest.mark.django_db
def test_la_ficha_y_el_calendario_tienen_reprogramar(client: Client, partido: Partido) -> None:
    org = entrar(client, ORGANIZACION)
    url = f"/partidos/{partido.pk}/reprogramar/"
    assert url in org.get(f"/partidos/{partido.pk}/ficha/").content.decode()
    dia = timezone.localtime(partido.inicio).date().isoformat()
    assert url in org.get(f"/calendario/{dia}/").content.decode()


@pytest.mark.django_db
def test_la_pantalla_pide_el_motivo_sin_pedidos_particulares(
    client: Client, partido: Partido
) -> None:
    html = entrar(client, ORGANIZACION).get(f"/partidos/{partido.pk}/reprogramar/").content
    texto = html.decode()
    assert "Partido de la ACF" in texto and "Decisión de la organización" in texto
    assert f"/partidos/{partido.pk}/mover/" in texto
    assert f"/partidos/{partido.pk}/intercambiar/" in texto


@pytest.mark.django_db
def test_un_equipo_no_puede_crea_el_bloqueo_y_lleva_a_las_propuestas(
    client: Client, partido: Partido
) -> None:
    org = entrar(client, ORGANIZACION)
    respuesta = org.post(
        f"/partidos/{partido.pk}/reprogramar/",
        {"motivo": "Partido de la ACF", "equipos": [partido.local_id]},
    )
    bloqueo = Bloqueo.objects.get()
    assert list(bloqueo.equipos.all()) == [partido.local]
    assert bloqueo.motivo == "Partido de la ACF"
    assert bloqueo.inicio == partido.inicio
    corrida = Corrida.objects.filter(tipo=Corrida.Tipo.REPROGRAMAR).get()
    assert respuesta["Location"] == f"/corridas/{corrida.pk}/propuestas/"


@pytest.mark.django_db
def test_sin_elegir_equipos_no_hace_nada(client: Client, partido: Partido) -> None:
    org = entrar(client, ORGANIZACION)
    respuesta = org.post(f"/partidos/{partido.pk}/reprogramar/", {"motivo": "Partido de la ACF"})
    assert respuesta.status_code == 200
    assert not Bloqueo.objects.exists()


@pytest.mark.django_db
def test_la_mesa_no_reprograma(client: Client, partido: Partido) -> None:
    mesa = entrar(client, MESA)
    assert mesa.get(f"/partidos/{partido.pk}/reprogramar/").status_code == 403
    assert (
        f"/partidos/{partido.pk}/reprogramar/"
        not in mesa.get(f"/partidos/{partido.pk}/ficha/").content.decode()
    )


@pytest.mark.django_db
def test_la_pantalla_de_la_acf_se_llama_un_equipo_no_puede_jugar(
    client: Client, torneo: Torneo
) -> None:
    org = entrar(client, ORGANIZACION)
    html = org.get(f"/torneos/{torneo.pk}/acf/").content.decode()
    assert "Un equipo no puede jugar" in html
    # T13.20: el formulario aparece después de elegir el club.
    club = Club.objects.first()
    assert club is not None
    html = org.get(f"/torneos/{torneo.pk}/acf/?club={club.pk}").content.decode()
    assert "Decisión de la organización" in html  # el motivo es una lista
    assert "Un equipo no puede jugar" in org.get("/").content.decode()
