"""T8.11: equipo, patrocinadores y caché de la página pública (B7, P66, P69). Datos inventados."""

import io
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.test import Client
from PIL import Image

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Jugador, Patrocinador, Persona, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion


def webp() -> ContentFile[bytes]:
    salida = io.BytesIO()
    Image.new("RGB", (40, 40), (1, 2, 3)).save(salida, "WEBP")
    return ContentFile(salida.getvalue(), name="x.webp")


@pytest.fixture
def equipo() -> Equipo:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    torneo.publico = True
    torneo.save()
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    equipo = Equipo.objects.create(
        club=Club.objects.create(nombre="River"), categoria=cn, nombre="River"
    )
    for i, autorizada in enumerate([True, False]):
        persona = Persona.objects.create(
            nombres=f"Nombre{i}", apellidos="Apellidoinventado", foto_autorizada=autorizada
        )
        persona.foto.save(f"foto{i}.webp", webp())
        Jugador.objects.create(persona=persona, equipo=equipo, dorsal=10 + i)
    return equipo


def url(equipo: Equipo) -> str:
    return f"/t/{equipo.categoria.torneo_id}/equipo/{equipo.pk}/"


@pytest.mark.django_db
def test_el_equipo_con_su_plantel_y_solo_las_fotos_autorizadas(
    client: Client, equipo: Equipo
) -> None:
    html = client.get(url(equipo)).content.decode()
    autorizado, sin_autorizar = (j.persona for j in equipo.jugadores.order_by("dorsal"))
    assert "Nombre0 A." in html and "Nombre1 A." in html
    assert "Apellidoinventado" not in html
    assert f"/imagen/foto/{autorizado.pk}/" in html
    assert f"/imagen/foto/{sin_autorizar.pk}/" not in html


@pytest.mark.django_db
def test_la_pestana_equipos_enlaza_cada_equipo(client: Client, equipo: Equipo) -> None:
    pagina = f"/t/{equipo.categoria.torneo_id}/{equipo.categoria_id}/equipos/"
    assert url(equipo) in client.get(pagina).content.decode()


@pytest.mark.django_db
def test_patrocinadores_al_pie(client: Client, equipo: Equipo) -> None:
    patrocinador = Patrocinador.objects.create(
        torneo=equipo.categoria.torneo, nombre="Marca Inventada", imagen=webp(), orden=1
    )
    pagina = f"/t/{equipo.categoria.torneo_id}/{equipo.categoria_id}/partidos/"
    html = client.get(pagina).content.decode()
    assert f"/imagen/patrocinador/{patrocinador.pk}/" in html and "Marca Inventada" in html


@pytest.mark.django_db
def test_la_segunda_visita_no_consulta_la_base(
    client: Client, equipo: Equipo, django_assert_num_queries: Any
) -> None:
    pagina = f"/t/{equipo.categoria.torneo_id}/{equipo.categoria_id}/posiciones/"
    assert client.get(pagina).status_code == 200
    with django_assert_num_queries(0):
        assert client.get(pagina).status_code == 200


@pytest.mark.django_db
def test_el_fragmento_de_htmx_se_cachea_aparte(client: Client, equipo: Equipo) -> None:
    pagina = f"/t/{equipo.categoria.torneo_id}/{equipo.categoria_id}/partidos/"
    completa = client.get(pagina).content.decode()
    fragmento = client.get(pagina, headers={"HX-Request": "true"}).content.decode()
    assert "<html" in completa and "<html" not in fragmento


@pytest.mark.django_db
def test_las_paginas_internas_no_se_cachean(
    client: Client, equipo: Equipo, django_assert_max_num_queries: Any
) -> None:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    pagina = f"/equipos/{equipo.pk}/plantel/"
    client.get(pagina)
    respuesta = client.get(pagina)
    assert "max-age" not in respuesta.get("Cache-Control", "")
