"""T13.5 (P85): Organización y Mesa de control, separadas.

La mesa carga equipos y listas, verifica, lleva la ficha del partido y Hoy, y ve todo lo demás.
No toca reglas, fixture, programar, mover, reprogramar, bloqueos, suspender, borrar, retirar,
publicar, clubes, escuela, patrocinadores ni personas.

La matriz recorre todas las rutas: si una vista cambia de permiso, el test lo dice.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from django.contrib.auth.models import Group, User
from django.test import Client
from django.urls import URLPattern, URLResolver, get_resolver

from torneo.permisos import MESA, ORGANIZACION, PERMISOS_POR_ROL

# Las vistas que la mesa puede usar (módulo.función). Todas las demás con permiso son solo
# de la organización.
DE_LA_MESA = {
    "alta_rapida.alta_rapida",
    "calendario.suspendidos",
    "equipos.equipo",
    "equipos.nuevo_equipo",
    "ficha_partido.accion",
    "ficha_partido.ficha",
    "fotos.foto",
    "hoy.hoy",
    "jugadores.agregar_jugador",
    "jugadores.agregar_profe",
    "jugadores.revisar_jugador",
    "jugadores.revisar_profe",
    "jugadores.verificar",
    "mas.ver_historial",
    "pegar.pegar",
}


def _rutas(resolver: URLResolver | None = None) -> Iterator[URLPattern]:
    for patron in (resolver or get_resolver()).url_patterns:
        if isinstance(patron, URLResolver):
            yield from _rutas(patron)
        else:
            yield patron


def _con_permiso() -> dict[str, str]:
    vistas: dict[str, str] = {}
    for ruta in _rutas():
        vista: Any = ruta.callback
        permiso = getattr(vista, "permiso", None)
        if permiso and vista.__module__.startswith("torneo.views."):
            nombre = f"{vista.__module__.removeprefix('torneo.views.')}.{vista.__name__}"
            vistas[nombre] = permiso
    return vistas


def test_la_matriz_de_permisos_es_la_de_p85() -> None:
    vistas = _con_permiso()
    assert len(vistas) > 50  # todas las vistas con permiso, no solo algunas
    de_la_mesa = {f"torneo.{p}" for p in PERMISOS_POR_ROL[MESA]}
    mal = {
        nombre: permiso
        for nombre, permiso in vistas.items()
        if (permiso in de_la_mesa) != (nombre in DE_LA_MESA)
    }
    assert mal == {}
    assert set(vistas) >= DE_LA_MESA


def test_la_organizacion_tiene_todos_los_permisos() -> None:
    assert set(PERMISOS_POR_ROL[MESA]) <= set(PERMISOS_POR_ROL[ORGANIZACION])


@pytest.mark.django_db
@pytest.mark.parametrize("url", ["/clubes/", "/escuela/", "/personas/nueva/"])
def test_la_mesa_recibe_403_con_el_motivo(client: Client, url: str) -> None:
    usuario = User.objects.create_user("mesa", password="x")
    usuario.groups.add(Group.objects.get(name=MESA))
    client.force_login(usuario)
    respuesta = client.get(url)
    assert respuesta.status_code == 403
    assert "Solo la organización puede" in respuesta.content.decode()


@pytest.mark.django_db
def test_agregar_persona_ofrece_los_dos_roles_sin_decir_que_todos_hacen_todo(
    client: Client,
) -> None:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    html = client.get("/personas/nueva/").content.decode()
    assert "Mesa de control" in html and "Organización" in html
    assert "todos como Organización" not in html


@pytest.mark.django_db
def test_mas_no_le_muestra_clubes_a_la_mesa(client: Client) -> None:
    usuario = User.objects.create_user("mesa", password="x")
    usuario.groups.add(Group.objects.get(name=MESA))
    client.force_login(usuario)
    assert "/clubes/" not in client.get("/mas/").content.decode()


@pytest.fixture
def torneo_programado(settings: Any) -> Any:
    from django.conf import settings as conf

    from dominio.config import cargar_config
    from torneo.models import Club, Equipo
    from torneo.servicios.configuracion import cargar_configuracion
    from torneo.servicios.fixture import generar_fixture
    from torneo.servicios.programador import programar_torneo

    settings.RONDO_PROGRAMADOR_SEGUNDOS = 5
    torneo = cargar_configuracion(cargar_config(conf.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        club = Club.objects.create(nombre=f"Club {i}")
        Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}")
    generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    return torneo


@pytest.mark.django_db
def test_la_mesa_no_ve_acciones_de_la_organizacion(client: Client, torneo_programado: Any) -> None:
    """Recorre las pantallas de la mesa y resuelve cada enlace y formulario: ninguno lleva a
    una vista que solo puede usar la organización."""
    import re

    from django.urls import Resolver404, resolve
    from django.utils import timezone

    from torneo.models import Equipo, Partido

    usuario = User.objects.create_user("mesa", password="x")
    usuario.groups.add(Group.objects.get(name=MESA))
    client.force_login(usuario)
    partido = Partido.objects.filter(inicio__isnull=False).order_by("inicio").first()
    assert partido is not None and partido.inicio is not None
    dia = timezone.localtime(partido.inicio).date().isoformat()
    equipo = Equipo.objects.first()
    assert equipo is not None
    cn = partido.categoria_id
    paginas = [
        "/",
        "/mas/",
        "/hoy/",
        f"/calendario/{dia}/",
        f"/partidos/{partido.pk}/ficha/",
        f"/equipos/{equipo.pk}/plantel/",
        *(f"/torneo/{cn}/{p}/" for p in ("equipos", "fixture", "posiciones", "ajustes")),
    ]
    de_la_mesa = {f"torneo.{p}" for p in PERMISOS_POR_ROL[MESA]}
    prohibidos = []
    for pagina in paginas:
        respuesta = client.get(pagina)
        assert respuesta.status_code == 200, pagina
        for url in re.findall(
            r'(?:href|action|hx-post|hx-get)="(/[^"#?]*)', respuesta.content.decode()
        ):
            try:
                vista: Any = resolve(url).func
            except Resolver404:
                continue
            permiso = getattr(vista, "permiso", None)
            if permiso and permiso not in de_la_mesa:
                prohibidos.append((pagina, url))
    assert prohibidos == []
