"""T11.9 (P39): alta de un jugador en la cancha, desde la planilla, con la foto de la cámara.
Datos inventados."""

import io
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Jugador, Partido, Persona, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture


def foto() -> Any:
    salida = io.BytesIO()
    Image.new("RGB", (600, 800), (90, 120, 200)).save(salida, "JPEG")
    return SimpleUploadedFile("foto.jpg", salida.getvalue(), content_type="image/jpeg")


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


@pytest.fixture
def partido() -> Partido:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"E{i}"
        )
    generar_fixture(cn, semilla=1)
    p = cn.partidos.filter(fase="grupos").select_related("local").first()
    assert p is not None and p.local is not None
    return p


def url(partido: Partido) -> str:
    return f"/partidos/{partido.pk}/alta/{partido.local_id}/"


def datos(**cambios: Any) -> dict[str, Any]:
    return {
        "nombres": "Nombre",
        "apellidos": "Inventado",
        "documento": "7654321 LP",
        "nacimiento": "2017",
        "dorsal": "14",
    } | cambios


@pytest.mark.django_db
def test_la_planilla_lleva_al_alta_con_la_camara(org: Client, partido: Partido) -> None:
    html = org.get(f"/partidos/{partido.pk}/ficha/").content.decode()
    assert url(partido) in html
    formulario = org.get(url(partido)).content.decode()
    assert 'capture="environment"' in formulario


@pytest.mark.django_db
def test_se_inscribe_y_queda_jugando_con_su_dorsal_y_foto(org: Client, partido: Partido) -> None:
    respuesta = org.post(url(partido), datos(foto=foto()))
    assert respuesta.status_code == 302
    assert respuesta["Location"] == f"/partidos/{partido.pk}/ficha/"
    jugador = Jugador.objects.get(equipo=partido.local)
    assert partido.convocados.get(jugador=jugador).dorsal == 14
    persona = Persona.objects.get(pk=jugador.persona_id)
    assert persona.foto
    assert not persona.foto_autorizada  # se publica solo si la familia lo autoriza (P66)


@pytest.mark.django_db
def test_mismas_validaciones_con_confirmacion(org: Client, partido: Partido) -> None:
    assert partido.local is not None
    for i in range(14):
        persona = Persona.objects.create(nombres=f"N{i}", apellidos="Inventado")
        Jugador.objects.create(persona=persona, equipo=partido.local, dorsal=i + 1)
    respuesta = org.post(url(partido), datos())
    assert respuesta.status_code == 200
    assert "Guardar igual" in respuesta.content.decode()
    respuesta = org.post(url(partido), datos(confirmar="1"))
    assert respuesta.status_code == 302
    assert partido.local.jugadores.count() == 15


@pytest.mark.django_db
def test_un_error_de_edad_no_se_guarda(org: Client, partido: Partido) -> None:
    respuesta = org.post(url(partido), datos(nacimiento="2012"))
    assert respuesta.status_code == 200
    assert not Jugador.objects.exists()


@pytest.mark.django_db
def test_la_foto_se_cambia_desde_la_planilla_y_vuelve_al_partido(
    org: Client, partido: Partido
) -> None:
    assert partido.local is not None
    persona = Persona.objects.create(nombres="N", apellidos="Inventado")
    Jugador.objects.create(persona=persona, equipo=partido.local, dorsal=3)
    ficha = f"/partidos/{partido.pk}/ficha/"
    assert f"/personas/{persona.pk}/foto/?volver={ficha}" in org.get(ficha).content.decode()
    respuesta = org.post(f"/personas/{persona.pk}/foto/", {"foto": foto(), "volver": ficha})
    assert respuesta["Location"] == ficha
    # A otro lado no se vuelve.
    respuesta = org.post(f"/personas/{persona.pk}/foto/", {"volver": "https://otro.sitio/"})
    assert "otro.sitio" not in respuesta.get("Location", "")
