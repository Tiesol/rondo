"""T8.10: página pública en vivo, como Copa Fácil (B7, P65, P70, P71). Datos inventados.

Privacidad (P65): de cada jugador, "Nombre I." y dorsal. Nunca el CI, la fecha de nacimiento
ni el apellido completo, en ninguna página pública.
"""

from datetime import date

import pytest
from django.conf import settings
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Jugador, Partido, Persona, Torneo
from torneo.servicios import partido as servicio
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture

APELLIDO = "Zubizarretainventado"
CI = "9876543"
NACIMIENTO = date(2017, 3, 14)


@pytest.fixture
def categoria() -> CategoriaNivel:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    torneo.publico = True
    torneo.save()
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        equipo = Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
        persona = Persona.objects.create(
            nombres=f"Mateo{i}",
            apellidos=f"{APELLIDO} Segundo",
            tipo_documento="ci",
            documento=f"{CI}{i}",
            clave_documento=f"{CI}{i}",
            nacimiento=NACIMIENTO,
        )
        Jugador.objects.create(persona=persona, equipo=equipo, dorsal=9)
    generar_fixture(cn, semilla=1)
    return cn


def jugado(categoria: CategoriaNivel) -> Partido:
    partido = categoria.partidos.filter(fase="grupos").first()
    assert partido is not None and partido.local is not None and partido.visitante is not None
    goleador = partido.local.jugadores.first()
    servicio.empezar(partido, None)
    servicio.anotar(partido, "gol", partido.local, goleador, None)
    servicio.anotar(partido, "gol", partido.local, goleador, None)
    servicio.anotar(partido, "gol_en_contra", partido.local, None, None)
    servicio.anotar(
        partido, "amarilla", partido.visitante, partido.visitante.jugadores.first(), None
    )
    servicio.mejor_jugador(partido, goleador)
    servicio.terminar(partido, None)
    return partido


def url(categoria: CategoriaNivel, pestana: str) -> str:
    return f"/t/{categoria.torneo_id}/{categoria.pk}/{pestana}/"


@pytest.mark.django_db
def test_partidos_con_resultado_y_enlace_a_la_ficha(
    client: Client, categoria: CategoriaNivel
) -> None:
    partido = jugado(categoria)
    html = client.get(url(categoria, "partidos")).content.decode()
    assert 'aria-label="2 a 1"' in html
    assert f"/t/{categoria.torneo_id}/partido/{partido.pk}/" in html


@pytest.mark.django_db
def test_la_ficha_publica_muestra_goles_tarjetas_y_mejor_jugador(
    client: Client, categoria: CategoriaNivel
) -> None:
    partido = jugado(categoria)
    html = client.get(f"/t/{categoria.torneo_id}/partido/{partido.pk}/").content.decode()
    assert "Mateo" in html and f"Mateo{partido.local.nombre[-1]} Z." in html  # type: ignore[union-attr]
    assert "Gol en contra" in html and "Amarilla" in html and "Mejor jugador" in html


@pytest.mark.django_db
def test_goleadores_por_categoria(client: Client, categoria: CategoriaNivel) -> None:
    partido = jugado(categoria)
    html = client.get(url(categoria, "goleadores")).content.decode()
    numero = partido.local.nombre[-1]  # type: ignore[union-attr]
    assert f"Mateo{numero} Z." in html
    assert 'aria-label="2 goles"' in html


@pytest.mark.django_db
def test_posiciones_con_la_tabla(client: Client, categoria: CategoriaNivel) -> None:
    jugado(categoria)
    html = client.get(url(categoria, "posiciones")).content.decode()
    assert "Pts" in html and "Equipo 0" in html


@pytest.mark.django_db
def test_se_actualiza_sola_cada_30_segundos(client: Client, categoria: CategoriaNivel) -> None:
    html = client.get(url(categoria, "partidos")).content.decode()
    assert 'hx-trigger="every 30s"' in html  # P73 (T11.14)


@pytest.mark.django_db
def test_partidos_de_hoy(client: Client, categoria: CategoriaNivel) -> None:
    partido = jugado(categoria)
    partido.inicio = timezone.now()
    partido.save()
    html = client.get(f"/t/{categoria.torneo_id}/hoy/").content.decode()
    assert 'aria-label="2 a 1"' in html


@pytest.mark.django_db
def test_ninguna_pagina_publica_muestra_apellido_ci_ni_fecha(
    client: Client, categoria: CategoriaNivel
) -> None:
    partido = jugado(categoria)
    paginas = [
        url(categoria, pestana) for pestana in ("partidos", "posiciones", "goleadores", "equipos")
    ] + [f"/t/{categoria.torneo_id}/partido/{partido.pk}/", f"/t/{categoria.torneo_id}/hoy/"]
    for pagina in paginas:
        respuesta = client.get(pagina)
        assert respuesta.status_code == 200, pagina
        html = respuesta.content.decode()
        for prohibido in (APELLIDO, CI, "14/03/2017", "2017-03-14", "Segundo"):
            assert prohibido not in html, (pagina, prohibido)


@pytest.mark.django_db
def test_un_torneo_sin_publicar_no_muestra_la_ficha(
    client: Client, categoria: CategoriaNivel
) -> None:
    partido = jugado(categoria)
    Torneo.objects.filter(pk=categoria.torneo_id).update(publico=False)
    assert client.get(f"/t/{categoria.torneo_id}/partido/{partido.pk}/").status_code == 404
    assert client.get(f"/t/{categoria.torneo_id}/hoy/").status_code == 404
