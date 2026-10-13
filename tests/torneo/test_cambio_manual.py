"""T5.4: mover un partido a mano, con el verificador antes de guardar. Datos inventados."""

from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import Cambio, CategoriaNivel, Club, Equipo, Partido, Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo, verificar_torneo


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
    programar_torneo(torneo)
    return torneo


def entrar(client: Client, grupo: str) -> Client:
    usuario = User.objects.create_user(grupo[:4], password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


def programados() -> list[Partido]:
    return list(
        Partido.objects.filter(inicio__isnull=False, local__isnull=False)
        .select_related("cancha")
        .order_by("inicio")
    )


def datos(inicio: Any, cancha: str) -> dict[str, str]:
    local = timezone.localtime(inicio)
    return {"dia": local.date().isoformat(), "hora": local.strftime("%H:%M"), "cancha": cancha}


@pytest.mark.django_db
def test_mover_a_un_turno_libre_lo_guarda_sin_fijarlo(client: Client, torneo: Torneo) -> None:
    partido = programados()[0]
    ocupados = {timezone.localtime(p.inicio).date() for p in programados() if p.inicio}
    libre = next(
        f
        for f in torneo.franjas.order_by("inicio")
        if timezone.localtime(f.inicio).date() not in ocupados
    )
    destino = libre.inicio  # un día sin partidos: no choca con nada
    respuesta = entrar(client, ORGANIZACION).post(
        f"/partidos/{partido.pk}/mover/", datos(destino, "C2")
    )
    assert respuesta.status_code == 302
    partido.refresh_from_db()
    assert partido.inicio == destino
    cambio = Cambio.objects.get()
    assert cambio.motivo == "Cambio a mano"
    assert verificar_torneo(torneo) == {}


@pytest.mark.django_db
def test_mover_encima_de_otro_muestra_el_choque_y_no_guarda(client: Client, torneo: Torneo) -> None:
    uno, otro = programados()[:2]
    assert otro.cancha is not None
    antes = (uno.cancha_id, uno.inicio)
    respuesta = entrar(client, ORGANIZACION).post(
        f"/partidos/{uno.pk}/mover/", datos(otro.inicio, otro.cancha.codigo)
    )
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert "No se puede" in html
    assert "Se pisan en" in html or "a la vez" in html
    assert "Mover igual" not in html  # T11.2: lo físicamente imposible no se confirma
    uno.refresh_from_db()
    assert (uno.cancha_id, uno.inicio) == antes
    assert not Cambio.objects.exists()


@pytest.mark.django_db
def test_la_mesa_no_mueve_partidos(client: Client, torneo: Torneo) -> None:
    partido = programados()[0]
    respuesta = entrar(client, MESA).get(f"/partidos/{partido.pk}/mover/")
    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_el_calendario_ofrece_mover_solo_a_la_organizacion(client: Client, torneo: Torneo) -> None:
    partido = programados()[0]
    dia = timezone.localtime(partido.inicio).date().isoformat()
    org = entrar(client, ORGANIZACION)
    assert f"/partidos/{partido.pk}/mover/" in org.get(f"/calendario/{dia}/").content.decode()


# ---------- T11.2: avisos que se confirman ----------


def sabado(torneo: Torneo, hora: str) -> Any:
    from datetime import datetime, time, timedelta

    franja = torneo.franjas.order_by("inicio").first()
    assert franja is not None
    primero = timezone.localtime(franja.inicio).date()
    while primero.weekday() != 5:
        primero += timedelta(days=1)
    return timezone.make_aware(datetime.combine(primero, time.fromisoformat(hora)))


@pytest.mark.django_db
@pytest.mark.parametrize("hora", ["17:00", "07:00"])
def test_t11_2_fuera_de_horario_avisa_y_se_mueve_al_confirmar(
    client: Client, torneo: Torneo, hora: str
) -> None:
    partido = programados()[0]
    destino = sabado(torneo, hora)
    org = entrar(client, ORGANIZACION)
    respuesta = org.post(f"/partidos/{partido.pk}/mover/", datos(destino, "C2"))
    html = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert "Fuera de las franjas" in html
    assert "Mover igual" in html
    partido.refresh_from_db()
    assert partido.inicio != destino

    respuesta = org.post(
        f"/partidos/{partido.pk}/mover/", datos(destino, "C2") | {"confirmar": "1"}
    )
    assert respuesta.status_code == 302
    partido.refresh_from_db()
    assert partido.inicio == destino
    assert Cambio.objects.get().motivo == "Cambio a mano"


@pytest.mark.django_db
def test_t11_2_un_partido_sin_lugar_se_ubica_a_mano(client: Client, torneo: Torneo) -> None:
    from torneo.servicios.reprogramar import mover_a_mano

    partido = programados()[0]
    partido.cancha, partido.inicio = None, None
    partido.estado = Partido.Estado.PENDIENTE
    partido.save()
    cancha = torneo.canchas.get(codigo="C3")
    mover_a_mano(partido, cancha, sabado(torneo, "16:50"), confirmar=True)
    partido.refresh_from_db()
    assert partido.estado == Partido.Estado.PROGRAMADO
    assert partido.cancha == cancha


@pytest.mark.django_db
def test_t11_2_un_partido_empezado_no_se_mueve(client: Client, torneo: Torneo) -> None:
    partido = programados()[0]
    partido.estado = Partido.Estado.EN_JUEGO
    partido.save()
    respuesta = entrar(client, ORGANIZACION).post(
        f"/partidos/{partido.pk}/mover/",
        datos(sabado(torneo, "17:00"), "C2") | {"confirmar": "1"},
    )
    assert respuesta.status_code == 200
    assert "ya empezó" in respuesta.content.decode()
    assert not Cambio.objects.exists()


@pytest.mark.django_db
def test_t11_2_volver_a_programar_mueve_tambien_lo_movido_a_mano(torneo: Torneo) -> None:
    from torneo.servicios.reprogramar import mover_a_mano

    partido = programados()[0]
    mover_a_mano(partido, torneo.canchas.get(codigo="C2"), sabado(torneo, "17:00"), confirmar=True)
    programar_torneo(torneo)
    partido.refresh_from_db()
    assert partido.inicio != sabado(torneo, "17:00")  # 1.4: no hay partidos fijados a mano


@pytest.mark.django_db
def test_t11_2_los_sin_lugar_tienen_ubicar_hasta_que_se_ubican(
    client: Client, torneo: Torneo
) -> None:
    from torneo.servicios.reprogramar import mover_a_mano

    torneo.categorias.get(categoria="Sub 9", nivel="avanzado").canchas.clear()
    programar_torneo(torneo)
    org = entrar(client, ORGANIZACION)
    sin_lugar = Partido.objects.filter(estado=Partido.Estado.PENDIENTE, local__isnull=False)
    partido = sin_lugar.first()
    assert partido is not None
    html = org.get(f"/torneos/{torneo.pk}/programar/").content.decode()
    assert f"/partidos/{partido.pk}/mover/" in html

    mover_a_mano(partido, torneo.canchas.get(codigo="C3"), sabado(torneo, "17:00"), confirmar=True)
    html = org.get(f"/torneos/{torneo.pk}/programar/").content.decode()
    assert f"/partidos/{partido.pk}/mover/" not in html


@pytest.mark.django_db
def test_t11_3_se_mueve_a_media_cancha_2_con_aviso(client: Client, torneo: Torneo) -> None:
    partido = programados()[0]
    destino = sabado(torneo, "17:00")
    org = entrar(client, ORGANIZACION)
    html = org.post(f"/partidos/{partido.pk}/mover/", datos(destino, "C2A")).content.decode()
    assert "no juega en C2A" in html
    respuesta = org.post(
        f"/partidos/{partido.pk}/mover/", datos(destino, "C2A") | {"confirmar": "1"}
    )
    assert respuesta.status_code == 302
    partido.refresh_from_db()
    assert partido.cancha is not None and partido.cancha.codigo == "C2A"


@pytest.mark.django_db
def test_t11_3_el_selector_nombra_las_mitades(client: Client, torneo: Torneo) -> None:
    partido = programados()[0]
    html = entrar(client, ORGANIZACION).get(f"/partidos/{partido.pk}/mover/").content.decode()
    for nombre in ("Cancha 1 · mitad A", "Cancha 2 · mitad B", "Cancha 3 · mitad A"):
        assert nombre in html
