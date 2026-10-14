"""T8.6: la ficha del partido para cargarlo desde el celular. Datos inventados."""

from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Evento, Jugador, Partido, Persona, Torneo
from torneo.permisos import MESA
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10
    settings.PROGRAMADOR_TRABAJADORES = 4


@pytest.fixture
def partido() -> Partido:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        equipo = Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
        for d in (7, 10):
            persona = Persona.objects.create(nombres=f"Nombre{i}{d}", apellidos="Inventado")
            Jugador.objects.create(persona=persona, equipo=equipo, dorsal=d)
    generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    p = cn.partidos.filter(fase="grupos", inicio__isnull=False).first()
    assert p is not None
    return p


@pytest.fixture
def mesa(client: Client) -> Client:
    usuario = User.objects.create_user("mesa", password="x")
    usuario.groups.add(Group.objects.get(name=MESA))
    client.force_login(usuario)
    return client


def url(partido: Partido, que: str = "") -> str:
    return f"/partidos/{partido.pk}/ficha/{que}"


def hacer(cliente: Client, partido: Partido, **datos: Any) -> Any:
    return cliente.post(url(partido, "accion/"), datos, follow=True)


@pytest.mark.django_db
def test_la_ficha_muestra_los_botones_y_las_listas(mesa: Client, partido: Partido) -> None:
    mesa.post(url(partido, "accion/"), {"accion": "empezar"})
    html = mesa.get(url(partido)).content.decode()
    for texto in ("Gol", "Amarilla", "Roja", "Deshacer", "Terminar"):
        assert texto in html
    assert "Nombre" in html and ">7<" in html  # dorsal y nombre de cada jugador


@pytest.mark.django_db
def test_un_partido_completo_desde_la_ficha(mesa: Client, partido: Partido) -> None:
    assert partido.local is not None
    goleador = partido.local.jugadores.first()
    assert goleador is not None
    mesa.post(url(partido, "accion/"), {"accion": "empezar"})
    hacer(mesa, partido, accion="gol", equipo=partido.local_id, jugador=goleador.pk)
    mesa.post(url(partido, "accion/"), {"accion": "gol_en_contra", "equipo": partido.local_id})
    hacer(mesa, partido, accion="amarilla", equipo=partido.local_id, jugador=goleador.pk)
    html = mesa.get(url(partido)).content.decode()
    assert 'aria-label="1 a 1"' in html
    mesa.post(url(partido, "accion/"), {"accion": "deshacer"})
    assert Evento.objects.filter(partido=partido).count() == 2
    mesa.post(url(partido, "accion/"), {"accion": "mejor", "jugador": goleador.pk})
    mesa.post(url(partido, "accion/"), {"accion": "terminar", "confirmado": "1"})
    partido.refresh_from_db()
    assert partido.estado == Partido.Estado.JUGADO and partido.mejor_jugador == goleador


@pytest.mark.django_db
def test_wo_desde_la_ficha(mesa: Client, partido: Partido) -> None:
    mesa.post(
        url(partido, "accion/"), {"accion": "wo", "no_se_presento": "visitante", "confirmado": "1"}
    )
    partido.refresh_from_db()
    assert partido.estado == Partido.Estado.JUGADO and partido.no_se_presento == "visitante"
    assert 'aria-label="3 a 0"' in mesa.get(url(partido)).content.decode()


@pytest.mark.django_db
def test_un_error_se_muestra_sin_romper(mesa: Client, partido: Partido) -> None:
    respuesta = hacer(mesa, partido, accion="gol", equipo=partido.local_id)
    assert "todavía no empezó" in respuesta.content.decode()


@pytest.mark.django_db
def test_el_partido_terminado_no_se_mueve_al_reprogramar(mesa: Client, partido: Partido) -> None:
    antes = (partido.cancha_id, partido.inicio)
    mesa.post(url(partido, "accion/"), {"accion": "empezar"})
    mesa.post(url(partido, "accion/"), {"accion": "terminar", "confirmado": "1"})
    programar_torneo(partido.categoria.torneo)
    partido.refresh_from_db()
    assert (partido.cancha_id, partido.inicio) == antes


@pytest.mark.django_db
def test_el_calendario_del_dia_enlaza_la_ficha(mesa: Client, partido: Partido) -> None:
    assert partido.inicio is not None
    dia = timezone.localtime(partido.inicio).date().isoformat()
    assert url(partido) in mesa.get(f"/calendario/{dia}/").content.decode()


@pytest.mark.django_db
def test_sin_rol_no_se_ve_ni_se_carga(client: Client, partido: Partido) -> None:
    client.force_login(User.objects.create_user("nadie", password="x"))
    assert client.get(url(partido)).status_code == 403
    assert client.post(url(partido, "accion/"), {"accion": "empezar"}).status_code == 403


# ---------- B7 y B3 (fase 12): confirmar lo importante y reprogramar un partido en juego ----------


@pytest.mark.django_db
def test_b7_terminar_dice_con_que_marcador_y_no_hace_nada_sin_confirmar(
    mesa: Client, partido: Partido
) -> None:
    mesa.post(url(partido, "accion/"), {"accion": "empezar"})
    respuesta = mesa.post(url(partido, "accion/"), {"accion": "terminar"})
    html = respuesta.content.decode()
    assert "¿Estás seguro?" in html and "con el marcador 0 a 0" in html
    assert 'name="accion" value="terminar"' in html
    partido.refresh_from_db()
    assert partido.estado == "en_juego"


@pytest.mark.django_db
def test_b7_wo_y_borrar_un_evento_piden_confirmar(mesa: Client, partido: Partido) -> None:
    respuesta = mesa.post(url(partido, "accion/"), {"accion": "wo", "no_se_presento": "visitante"})
    assert "pierde por W.O." in respuesta.content.decode()
    partido.refresh_from_db()
    assert partido.estado != "jugado"


@pytest.mark.django_db
def test_b3_reprogramar_un_partido_en_juego_borra_sus_eventos_con_historial(
    mesa: Client, partido: Partido
) -> None:
    from django.utils import timezone

    from torneo.models import Evento, Registro

    mesa.post(url(partido, "accion/"), {"accion": "empezar"})
    assert partido.local is not None
    Evento.objects.create(partido=partido, tipo="gol", equipo=partido.local)
    Partido.objects.filter(pk=partido.pk).update(inicio=timezone.now())
    # Sin el día suspendido no se ofrece.
    assert "reprogramar_en_juego" not in mesa.get(url(partido, "")).content.decode()
    datos = {"accion": "reprogramar_en_juego"}
    respuesta = mesa.post(url(partido, "accion/"), datos)
    assert "Se borran sus 1 eventos" in respuesta.content.decode()
    respuesta = mesa.post(url(partido, "accion/"), datos | {"confirmado": "1"})
    assert respuesta["Location"] == f"/partidos/{partido.pk}/mover/"  # a ubicarlo
    partido.refresh_from_db()
    assert (partido.estado, partido.inicio, partido.cancha) == ("pendiente", None, None)
    assert not partido.eventos.exists()
    quedan = set(Registro.objects.filter(partido=partido).values_list("que", flat=True))
    assert {"Reprogramado en juego", "Borró: Gol"} <= quedan
