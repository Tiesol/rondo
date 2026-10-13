"""T11.8 (P9): la planilla del partido. Quiénes juegan y con qué dorsal en ESTE partido.
Datos inventados."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import IntegrityError, transaction
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Jugador, Partido, Persona, Registro, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios import partido as servicio
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.planilla import (
    NoSePuede,
    PideConfirmar,
    dorsal_sugerido,
    guardar_planilla,
)
from torneo.servicios.suspensiones import suspender_a_mano


@pytest.fixture
def usuario() -> User:
    usuario = User.objects.create_user("ana", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    return usuario


@pytest.fixture
def categoria() -> object:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        equipo = Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"E{i}"
        )
        for d in (7, 10, 11):
            persona = Persona.objects.create(nombres=f"N{i}{d}", apellidos="Inventado")
            Jugador.objects.create(persona=persona, equipo=equipo, dorsal=d)
    generar_fixture(cn, semilla=1)
    return cn


def de_un_equipo(categoria: object) -> tuple[Equipo, Partido, Partido]:
    """Un equipo y dos de sus partidos, en orden de fecha."""
    equipo = Equipo.objects.get(nombre="E0")
    suyos = list(
        Partido.objects.filter(fase="grupos", local=equipo)
        | Partido.objects.filter(fase="grupos", visitante=equipo)
    )
    suyos.sort(key=lambda p: p.fecha or 0)
    return equipo, suyos[0], suyos[1]


def filas(equipo: Equipo, dorsales: dict[int, int | None]) -> dict[int, int | None]:
    """{pk del jugador: dorsal} a partir de {dorsal habitual: dorsal del partido}."""
    return {equipo.jugadores.get(dorsal=h).pk: d for h, d in dorsales.items()}


@pytest.mark.django_db
def test_se_eligen_los_que_juegan_con_el_dorsal_del_partido(
    categoria: object, usuario: User
) -> None:
    equipo, partido, _ = de_un_equipo(categoria)
    guardar_planilla(partido, equipo, filas(equipo, {7: 7, 10: 23}), usuario)
    convocados = {c.jugador.dorsal: c.dorsal for c in partido.convocados.select_related("jugador")}
    assert convocados == {7: 7, 10: 23}
    # El habitual no cambia: el dorsal es de cada partido.
    assert equipo.jugadores.get(persona__nombres="N010").dorsal == 10
    assert Registro.objects.filter(partido=partido, que="Juega").count() == 2


@pytest.mark.django_db
def test_un_dorsal_repetido_no_se_guarda(categoria: object, usuario: User) -> None:
    equipo, partido, _ = de_un_equipo(categoria)
    with pytest.raises(NoSePuede, match="El 7"):
        guardar_planilla(partido, equipo, filas(equipo, {7: 7, 10: 7}), usuario)
    assert not partido.convocados.exists()
    # Y la base tampoco lo deja (P9: imposible).
    guardar_planilla(partido, equipo, filas(equipo, {7: 7, 10: 10}), usuario)
    otro = partido.convocados.get(dorsal=10)
    otro.dorsal = 7
    with pytest.raises(IntegrityError), transaction.atomic():
        otro.save()


@pytest.mark.django_db
def test_sacar_a_uno_de_la_planilla(categoria: object, usuario: User) -> None:
    equipo, partido, _ = de_un_equipo(categoria)
    guardar_planilla(partido, equipo, filas(equipo, {7: 7, 10: 10}), usuario)
    guardar_planilla(partido, equipo, filas(equipo, {7: 7}), usuario)
    assert [c.dorsal for c in partido.convocados.all()] == [7]


@pytest.mark.django_db
def test_el_dorsal_sugerido_es_el_del_partido_anterior(categoria: object, usuario: User) -> None:
    equipo, primero, segundo = de_un_equipo(categoria)
    jugador = equipo.jugadores.get(dorsal=10)
    assert dorsal_sugerido(primero, jugador) == 10  # el habitual
    guardar_planilla(primero, equipo, {jugador.pk: 5}, usuario)
    assert dorsal_sugerido(segundo, jugador) == 5


@pytest.mark.django_db
def test_un_suspendido_se_convoca_solo_confirmando(categoria: object, usuario: User) -> None:
    equipo, primero, segundo = de_un_equipo(categoria)
    jugador = equipo.jugadores.get(dorsal=7)
    suspender_a_mano(primero, jugador, partidos=1, motivo="Roja directa", usuario=usuario)
    with pytest.raises(PideConfirmar, match="suspendido"):
        guardar_planilla(segundo, equipo, {jugador.pk: 7}, usuario)
    guardar_planilla(segundo, equipo, {jugador.pk: 7}, usuario, confirmado=True)
    assert segundo.convocados.filter(jugador=jugador).exists()


@pytest.mark.django_db
def test_un_gol_de_alguien_que_no_estaba_en_la_planilla_lo_suma(
    categoria: object, usuario: User
) -> None:
    equipo, partido, _ = de_un_equipo(categoria)
    servicio.empezar(partido, usuario)
    jugador = equipo.jugadores.get(dorsal=11)
    servicio.anotar(partido, "gol", equipo, jugador, usuario)
    assert partido.convocados.get(jugador=jugador).dorsal == 11


@pytest.mark.django_db
def test_la_ficha_tiene_la_planilla_antes_de_empezar(
    client: Client, categoria: object, usuario: User
) -> None:
    equipo, partido, _ = de_un_equipo(categoria)
    client.force_login(usuario)
    url = f"/partidos/{partido.pk}/ficha/"
    html = client.get(url).content.decode()
    assert "Planilla" in html
    jugador = equipo.jugadores.get(dorsal=7)
    datos = {
        "accion": "planilla",
        "equipo": equipo.pk,
        f"juega_{jugador.pk}": "on",
        f"dorsal_{jugador.pk}": "9",
        "entrenador": "on",
    }
    client.post(f"/partidos/{partido.pk}/ficha/accion/", datos)
    assert partido.convocados.get().dorsal == 9
    partido.refresh_from_db()
    lado = "local" if partido.local_id == equipo.pk else "visitante"
    assert getattr(partido, f"entrenador_{lado}") is True


@pytest.mark.django_db
def test_todos_juegan_con_un_toque(client: Client, categoria: object, usuario: User) -> None:
    equipo, partido, _ = de_un_equipo(categoria)
    client.force_login(usuario)
    datos = {"accion": "planilla", "equipo": equipo.pk, "todos": "1"}
    client.post(f"/partidos/{partido.pk}/ficha/accion/", datos)
    assert sorted(c.dorsal or 0 for c in partido.convocados.all()) == [7, 10, 11]


@pytest.mark.django_db
def test_cambiar_el_dorsal_durante_el_partido(
    client: Client, categoria: object, usuario: User
) -> None:
    equipo, partido, _ = de_un_equipo(categoria)
    guardar_planilla(partido, equipo, filas(equipo, {7: 7, 10: 10}), usuario)
    servicio.empezar(partido, usuario)
    jugador = equipo.jugadores.get(dorsal=7)
    url = f"/partidos/{partido.pk}/ficha/accion/"
    client.force_login(usuario)
    respuesta = client.post(
        url, {"accion": "dorsal", "jugador": jugador.pk, "dorsal": "10"}, follow=True
    )
    assert "El 10 ya lo tiene" in respuesta.content.decode()
    client.post(url, {"accion": "dorsal", "jugador": jugador.pk, "dorsal": "23"})
    assert partido.convocados.get(jugador=jugador).dorsal == 23
    jugador.refresh_from_db()
    assert jugador.dorsal == 7  # el habitual queda
