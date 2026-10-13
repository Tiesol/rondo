"""T8.5: cargar un partido: estado, eventos, deshacer, W.O., penales y mejor jugador."""

import pytest
from django.conf import settings
from django.contrib.auth.models import User

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Evento, Jugador, Partido, Persona, Torneo
from torneo.servicios import partido as servicio
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.partido import NoSePuede


@pytest.fixture
def usuario() -> User:
    return User.objects.create_user("mesa", password="x")


def con_jugadores(equipo: Equipo, cantidad: int = 3) -> list[Jugador]:
    return [
        Jugador.objects.create(
            persona=Persona.objects.create(nombres=f"N{i}", apellidos="Inventado"),
            equipo=equipo,
            dorsal=i + 1,
        )
        for i in range(cantidad)
    ]


@pytest.fixture
def torneo() -> Torneo:
    return cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))


@pytest.fixture
def partido(torneo: Torneo) -> Partido:
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"E{i}"
        )
    generar_fixture(cn, semilla=1)
    p = cn.partidos.filter(fase="grupos").first()
    assert p is not None and p.local and p.visitante
    con_jugadores(p.local)
    con_jugadores(p.visitante)
    return p


@pytest.mark.django_db
def test_un_partido_completo(partido: Partido, usuario: User) -> None:
    servicio.empezar(partido, usuario)
    assert partido.estado == Partido.Estado.EN_JUEGO
    goleador = partido.local.jugadores.first()  # type: ignore[union-attr]
    servicio.anotar(partido, "gol", partido.local, goleador, usuario)  # type: ignore[arg-type]
    servicio.anotar(partido, "gol", partido.local, goleador, usuario)  # type: ignore[arg-type]
    servicio.anotar(partido, "gol_en_contra", partido.local, None, usuario)  # type: ignore[arg-type]
    amonestado = partido.visitante.jugadores.first()  # type: ignore[union-attr]
    servicio.anotar(partido, "amarilla", partido.visitante, amonestado, usuario)  # type: ignore[arg-type]
    assert servicio.resultado_de(partido).marcador == (2, 1)
    evento = Evento.objects.filter(partido=partido).last()
    assert evento is not None and evento.creado_por == usuario and evento.creado_en
    servicio.terminar(partido, usuario)
    assert partido.estado == Partido.Estado.JUGADO


@pytest.mark.django_db
def test_deshacer_quita_solo_el_ultimo(partido: Partido, usuario: User) -> None:
    servicio.empezar(partido, usuario)
    servicio.anotar(partido, "gol", partido.local, None, usuario)  # type: ignore[arg-type]
    servicio.anotar(partido, "gol", partido.visitante, None, usuario)  # type: ignore[arg-type]
    servicio.deshacer(partido)
    assert servicio.resultado_de(partido).marcador == (1, 0)


@pytest.mark.django_db
def test_un_jugador_de_otro_equipo_no_puede_figurar(partido: Partido, usuario: User) -> None:
    servicio.empezar(partido, usuario)
    del_visitante = partido.visitante.jugadores.first()  # type: ignore[union-attr]
    with pytest.raises(NoSePuede, match="no juega en"):
        servicio.anotar(partido, "gol", partido.local, del_visitante, usuario)  # type: ignore[arg-type]
    otro = Equipo.objects.exclude(pk__in=[partido.local_id, partido.visitante_id]).first()
    with pytest.raises(NoSePuede):
        servicio.anotar(partido, "gol", otro, None, usuario)  # type: ignore[arg-type]


@pytest.mark.django_db
def test_no_se_anota_en_un_partido_que_no_empezo(partido: Partido, usuario: User) -> None:
    with pytest.raises(NoSePuede, match="empez"):
        servicio.anotar(partido, "gol", partido.local, None, usuario)  # type: ignore[arg-type]


@pytest.mark.django_db
def test_wo_da_el_marcador_de_la_regla(partido: Partido, usuario: User) -> None:
    servicio.wo(partido, "visitante", usuario)
    assert partido.estado == Partido.Estado.JUGADO
    assert servicio.resultado_de(partido).marcador == (3, 0)  # P23


@pytest.mark.django_db
def test_en_la_eliminacion_un_empate_pide_penales(torneo: Torneo, usuario: User) -> None:
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    a, b = (
        Equipo.objects.create(club=Club.objects.create(nombre=n), categoria=cn, nombre=n)
        for n in "AB"
    )
    final = Partido.objects.create(
        categoria=cn, fase="eliminacion", clave="oro_final", local=a, visitante=b
    )
    servicio.empezar(final, usuario)
    with pytest.raises(NoSePuede, match="penales"):
        servicio.terminar(final, usuario)
    servicio.penales(final, 4, 3)
    servicio.terminar(final, usuario)
    assert servicio.resultado_de(final).ganador == "local"


@pytest.mark.django_db
def test_mejor_jugador_de_uno_de_los_dos_equipos(partido: Partido, usuario: User) -> None:
    jugador = partido.visitante.jugadores.first()  # type: ignore[union-attr]
    servicio.mejor_jugador(partido, jugador)
    assert Partido.objects.get(pk=partido.pk).mejor_jugador == jugador
    ajeno = Jugador.objects.exclude(equipo__in=[partido.local_id, partido.visitante_id]).first()
    if ajeno is not None:
        with pytest.raises(NoSePuede):
            servicio.mejor_jugador(partido, ajeno)


@pytest.mark.django_db
def test_un_partido_en_juego_no_se_reprograma(partido: Partido, usuario: User) -> None:
    servicio.empezar(partido, usuario)
    assert partido.empezado
    from torneo.servicios.fixture import FixtureNoSePuede

    with pytest.raises(FixtureNoSePuede):
        generar_fixture(partido.categoria)
