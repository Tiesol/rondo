"""T11.10: eventos con minuto, gol en contra con jugador (P72), lesión, "afuera 5 min" y el
partido terminado editable. Datos inventados."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Evento, Jugador, Partido, Persona, Registro, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios import partido as servicio
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.publico import ficha_publica, goleadores


@pytest.fixture
def usuario() -> User:
    usuario = User.objects.create_user("ana", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    return usuario


def partido_de(categoria: str = "Sub 9") -> Partido:
    torneo: Torneo = Torneo.objects.first() or cargar_configuracion(
        cargar_config(settings.PLANTILLA_TORNEO)
    )
    cn = torneo.categorias.get(categoria=categoria, nivel="avanzado")
    for i in range(4):
        equipo = Equipo.objects.create(
            club=Club.objects.get_or_create(nombre=f"Club {i}")[0], categoria=cn, nombre=f"E{i}"
        )
        for d in (7, 10):
            persona = Persona.objects.create(nombres=f"Nombre{i}{d}", apellidos="Inventado")
            Jugador.objects.create(persona=persona, equipo=equipo, dorsal=d)
    generar_fixture(cn, semilla=1)
    p = cn.partidos.filter(fase="grupos").select_related("local", "visitante").first()
    assert p is not None and p.local and p.visitante
    return p


def url(partido: Partido) -> str:
    return f"/partidos/{partido.pk}/ficha/accion/"


@pytest.mark.django_db
def test_el_minuto_sale_del_reloj_en_cada_tiempo(usuario: User) -> None:
    partido = partido_de()
    servicio.empezar(partido, usuario)
    Partido.objects.filter(pk=partido.pk).update(
        inicio_real=timezone.now() - timedelta(minutes=12, seconds=30)
    )
    partido.refresh_from_db()
    jugador = partido.local.jugadores.first()  # type: ignore[union-attr]
    gol = servicio.anotar(partido, "gol", partido.local, jugador, usuario)  # type: ignore[arg-type]
    assert gol.minuto == 13  # el minuto 13 en curso
    servicio.avanzar_tiempo(partido, usuario)
    servicio.avanzar_tiempo(partido, usuario)
    Partido.objects.filter(pk=partido.pk).update(
        fin_descanso=timezone.now() - timedelta(minutes=4, seconds=10)
    )
    partido.refresh_from_db()
    otro = servicio.anotar(partido, "gol", partido.local, jugador, usuario)  # type: ignore[arg-type]
    assert otro.minuto == partido.categoria.min_por_tiempo + 5


@pytest.mark.django_db
def test_el_gol_en_contra_lleva_al_jugador_y_no_cuenta_como_goleador(usuario: User) -> None:
    partido = partido_de()
    servicio.empezar(partido, usuario)
    jugador = partido.local.jugadores.first()  # type: ignore[union-attr]
    servicio.anotar(partido, "gol_en_contra", partido.local, jugador, usuario)  # type: ignore[arg-type]
    assert Evento.objects.get().jugador == jugador
    assert servicio.resultado_de(partido).marcador == (0, 1)
    assert goleadores(partido.categoria) == []


@pytest.mark.django_db
def test_lesion_y_amonestacion_nunca_son_publicas(usuario: User) -> None:
    partido = partido_de("Sub 7")
    servicio.empezar(partido, usuario)
    jugador = partido.local.jugadores.first()  # type: ignore[union-attr]
    servicio.anotar(partido, "lesion", partido.local, jugador, usuario)  # type: ignore[arg-type]
    servicio.anotar(partido, "amonestacion", partido.local, jugador, usuario)  # type: ignore[arg-type]
    servicio.anotar(partido, "amarilla", partido.local, jugador, usuario)  # type: ignore[arg-type]
    assert [e["tipo"] for e in ficha_publica(partido)["eventos"]] == ["Amarilla"]


@pytest.mark.django_db
def test_segunda_amarilla_hasta_sub_9_dice_cuando_vuelve(client: Client, usuario: User) -> None:
    partido = partido_de()
    servicio.empezar(partido, usuario)
    jugador = partido.local.jugadores.first()  # type: ignore[union-attr]
    for _ in range(2):
        segunda = servicio.anotar(partido, "amarilla", partido.local, jugador, usuario)  # type: ignore[arg-type]
    vuelve = timezone.localtime(segunda.creado_en + timedelta(minutes=5))
    client.force_login(usuario)
    html = client.get(f"/partidos/{partido.pk}/ficha/").content.decode()
    assert f"Afuera 5 min · vuelve {vuelve:%H:%M}" in html


@pytest.mark.django_db
def test_un_partido_terminado_se_corrige_con_historial(client: Client, usuario: User) -> None:
    partido = partido_de()
    servicio.empezar(partido, usuario)
    jugador = partido.local.jugadores.first()  # type: ignore[union-attr]
    gol = servicio.anotar(partido, "gol", partido.local, jugador, usuario)  # type: ignore[arg-type]
    amarilla = servicio.anotar(partido, "amarilla", partido.local, jugador, usuario)  # type: ignore[arg-type]
    servicio.terminar(partido, usuario)
    client.force_login(usuario)
    # Corregir el minuto y borrar un evento que no es el último.
    client.post(url(partido), {"accion": "minuto", "evento_id": gol.pk, "minuto": "33"})
    gol.refresh_from_db()
    assert gol.minuto == 33
    client.post(url(partido), {"accion": "borrar", "evento_id": gol.pk})
    assert list(Evento.objects.all()) == [amarilla]
    # Sumar un gol olvidado después de terminar.
    client.post(url(partido), {"evento": f"gol|{partido.local_id}|{jugador.pk}"})  # type: ignore[union-attr]
    assert servicio.resultado_de(partido).marcador == (1, 0)
    # Corregir la hora real del final.
    client.post(url(partido), {"accion": "horas", "fin_real": "18:05"})
    partido.refresh_from_db()
    assert timezone.localtime(partido.fin_real).strftime("%H:%M") == "18:05"
    hechos = set(Registro.objects.filter(partido=partido).values_list("que", flat=True))
    assert {"Minuto", "Borró: Gol", "Horas"} <= hechos


@pytest.mark.django_db
def test_un_wo_se_puede_quitar(client: Client, usuario: User) -> None:
    partido = partido_de()
    servicio.wo(partido, "local", usuario)
    client.force_login(usuario)
    client.post(url(partido), {"accion": "quitar_wo"})
    partido.refresh_from_db()
    assert partido.no_se_presento == ""
    assert not partido.empezado
