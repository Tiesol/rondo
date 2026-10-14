"""T11.8 (P9): la planilla del partido. Quiénes juegan y con qué dorsal en ESTE partido.
Datos inventados."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Jugador, Partido, Persona, Registro, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios import partido as servicio
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.planilla import (
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
def test_c1_un_dorsal_repetido_avisa_y_se_guarda_con_guardar_igual(
    categoria: object, usuario: User
) -> None:
    # C1 (fase 12): el dorsal repetido es un aviso, no un bloqueo.
    equipo, partido, _ = de_un_equipo(categoria)
    with pytest.raises(PideConfirmar, match=r"El 7 está repetido: N07 I\. y N010 I\.$"):
        guardar_planilla(partido, equipo, filas(equipo, {7: 7, 10: 7}), usuario)
    assert not partido.convocados.exists()
    guardar_planilla(partido, equipo, filas(equipo, {7: 7, 10: 7}), usuario, confirmado=True)
    assert sorted(c.dorsal or 0 for c in partido.convocados.all()) == [7, 7]


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


@pytest.mark.django_db
def test_c1_cambiar_el_dorsal_a_uno_repetido_pide_confirmar(
    client: Client, categoria: object, usuario: User
) -> None:
    equipo, partido, _ = de_un_equipo(categoria)
    guardar_planilla(partido, equipo, filas(equipo, {7: 7, 10: 10}), usuario)
    servicio.empezar(partido, usuario)
    jugador = equipo.jugadores.get(dorsal=7)
    client.force_login(usuario)
    url = f"/partidos/{partido.pk}/ficha/accion/"
    datos = {"accion": "dorsal", "jugador": jugador.pk, "dorsal": "10"}
    respuesta = client.post(url, datos)
    assert "El 10 ya lo tiene" in respuesta.content.decode()
    assert "Guardar igual" in respuesta.content.decode()
    assert partido.convocados.get(jugador=jugador).dorsal == 7
    client.post(url, datos | {"confirmar": "1"})
    assert partido.convocados.get(jugador=jugador).dorsal == 10


@pytest.mark.django_db
def test_c1_la_planilla_marca_los_repetidos_y_guarda_igual(
    client: Client, categoria: object, usuario: User
) -> None:
    equipo, partido, _ = de_un_equipo(categoria)
    client.force_login(usuario)
    a, b = equipo.jugadores.get(dorsal=7), equipo.jugadores.get(dorsal=10)
    datos = {
        "accion": "planilla",
        "equipo": equipo.pk,
        f"juega_{a.pk}": "on",
        f"dorsal_{a.pk}": "9",
        f"juega_{b.pk}": "on",
        f"dorsal_{b.pk}": "9",
    }
    respuesta = client.post(f"/partidos/{partido.pk}/ficha/accion/", datos)
    html = respuesta.content.decode()
    assert "El 9 está repetido" in html and "Guardar igual" in html
    assert not partido.convocados.exists()
    client.post(f"/partidos/{partido.pk}/ficha/accion/", datos | {"confirmar": "1"})
    assert partido.convocados.count() == 2
    # Ya guardados, la planilla los marca.
    assert "Repetido" in client.get(f"/partidos/{partido.pk}/ficha/").content.decode()


# ---------- C2 (fase 12): CI verificado en cada partido ----------


@pytest.mark.django_db
def test_c2_el_ci_se_verifica_por_partido_y_marca_al_jugador(
    categoria: object, usuario: User
) -> None:
    equipo, primero, segundo = de_un_equipo(categoria)
    a, b = equipo.jugadores.get(dorsal=7), equipo.jugadores.get(dorsal=10)
    guardar_planilla(primero, equipo, {a.pk: 7, b.pk: 10}, usuario, verificados={a.pk})
    assert {c.jugador_id: c.ci_verificado for c in primero.convocados.all()} == {
        a.pk: True,
        b.pk: False,
    }
    a.refresh_from_db()
    b.refresh_from_db()
    assert a.verificado and not b.verificado  # lo de la inscripción también se marca
    # En otro partido empieza sin verificar: es por partido.
    guardar_planilla(segundo, equipo, {a.pk: 7}, usuario)
    assert not segundo.convocados.get(jugador=a).ci_verificado
    # "Verificar todos".
    guardar_planilla(primero, equipo, {a.pk: 7, b.pk: 10}, usuario, verificar_todos=True)
    assert all(c.ci_verificado for c in primero.convocados.all())


@pytest.mark.django_db
def test_c2_la_planilla_muestra_el_ci_y_cuantos_estan_verificados(
    client: Client, categoria: object, usuario: User
) -> None:
    equipo, partido, _ = de_un_equipo(categoria)
    a, b = equipo.jugadores.get(dorsal=7), equipo.jugadores.get(dorsal=10)
    Persona.objects.filter(pk=a.persona_id).update(documento="1234567 SC")
    client.force_login(usuario)
    url = f"/partidos/{partido.pk}/ficha/accion/"
    base = {"accion": "planilla", "equipo": equipo.pk, f"juega_{a.pk}": "on", f"juega_{b.pk}": "on"}
    client.post(url, base | {f"ci_{a.pk}": "on", f"dorsal_{a.pk}": "7", f"dorsal_{b.pk}": "10"})
    html = client.get(f"/partidos/{partido.pk}/ficha/").content.decode()
    assert "1234567 SC" in html  # interno: se ve con sesión
    assert "1 de 2" in html
    client.post(url, base | {"verificar_todos": "1", f"dorsal_{a.pk}": "7", f"dorsal_{b.pk}": "10"})
    assert "2 de 2" in client.get(f"/partidos/{partido.pk}/ficha/").content.decode()
    # Nunca en lo público.
    torneo = partido.categoria.torneo
    torneo.publico = True
    torneo.save()
    publico = client.get(f"/t/{torneo.pk}/partido/{partido.pk}/").content.decode()
    assert "1234567" not in publico


@pytest.mark.django_db
def test_c1_al_anotar_un_gol_con_dorsal_repetido_se_elige_por_nombre(
    client: Client, categoria: object, usuario: User
) -> None:
    equipo, partido, _ = de_un_equipo(categoria)
    guardar_planilla(partido, equipo, filas(equipo, {7: 9, 10: 9}), usuario, confirmado=True)
    servicio.empezar(partido, usuario)
    client.force_login(usuario)
    html = client.get(f"/partidos/{partido.pk}/ficha/").content.decode()
    for nombre in ("N07 Inventado", "N010 Inventado"):
        assert nombre in html  # los dos con el 9, cada uno con su nombre
    assert html.count('class="btn jugador"') >= 2
