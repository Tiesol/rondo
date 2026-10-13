"""T8.3: escudo del club, logo del organizador y patrocinadores (P68, P69). Imágenes inventadas."""

import io
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Organizador, Patrocinador, Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion


def png(
    nombre: str = "escudo.png", color: tuple[int, int, int] = (10, 40, 90)
) -> SimpleUploadedFile:
    salida = io.BytesIO()
    Image.new("RGB", (900, 900), color).save(salida, "PNG")
    return SimpleUploadedFile(nombre, salida.getvalue(), content_type="image/png")


@pytest.fixture
def torneo() -> Torneo:
    return cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))


@pytest.fixture
def equipo(torneo: Torneo) -> Equipo:
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    club = Club.objects.create(nombre="River Plate")
    return Equipo.objects.create(club=club, categoria=cn, nombre="River Plate")


def entrar(client: Client, grupo: str) -> Client:
    usuario = User.objects.create_user(grupo[:4], password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


# ---------- Escudo del club (P68) ----------


@pytest.mark.django_db
def test_la_organizacion_sube_el_escudo_y_aparece_en_sus_equipos(
    client: Client, equipo: Equipo
) -> None:
    org = entrar(client, ORGANIZACION)
    org.post(f"/clubes/{equipo.club_id}/escudo/", {"escudo": png(), "equipo": equipo.pk})
    club = Club.objects.get(pk=equipo.club_id)
    assert (club.escudo.name or "").startswith("escudos/") and (club.escudo.name or "").endswith(
        ".webp"
    )
    ficha = org.get(f"/equipos/{equipo.pk}/plantel/").content.decode()
    assert f"/imagen/escudo/{club.pk}/" in ficha
    # Se sirve desde la app, sin login: no tiene datos personales.
    client.logout()
    respuesta = client.get(f"/imagen/escudo/{club.pk}/")
    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "image/webp"


@pytest.mark.django_db
def test_sin_escudo_se_ve_la_sigla(client: Client, equipo: Equipo) -> None:
    ficha = entrar(client, ORGANIZACION).get(f"/equipos/{equipo.pk}/plantel/").content.decode()
    assert "/imagen/escudo/" not in ficha and ">RIV<" in ficha
    assert client.get(f"/imagen/escudo/{equipo.club_id}/").status_code == 404


@pytest.mark.django_db
def test_reemplazar_el_escudo_borra_el_anterior(client: Client, equipo: Equipo) -> None:
    org = entrar(client, ORGANIZACION)
    org.post(f"/clubes/{equipo.club_id}/escudo/", {"escudo": png()})
    viejo = Club.objects.get(pk=equipo.club_id).escudo.name or ""
    org.post(f"/clubes/{equipo.club_id}/escudo/", {"escudo": png(color=(200, 0, 0))})
    nuevo = Club.objects.get(pk=equipo.club_id).escudo
    assert nuevo.name != viejo
    assert not nuevo.storage.exists(viejo)


@pytest.mark.django_db
def test_un_archivo_que_no_es_imagen_se_rechaza(client: Client, equipo: Equipo) -> None:
    org = entrar(client, ORGANIZACION)
    falso = SimpleUploadedFile("escudo.png", b"no soy una imagen", content_type="image/png")
    respuesta = org.post(f"/clubes/{equipo.club_id}/escudo/", {"escudo": falso}, follow=True)
    assert "JPG, PNG o WebP" in respuesta.content.decode()
    assert not Club.objects.get(pk=equipo.club_id).escudo


@pytest.mark.django_db
def test_la_mesa_no_sube_escudos(client: Client, equipo: Equipo) -> None:
    mesa = entrar(client, MESA)
    assert mesa.post(f"/clubes/{equipo.club_id}/escudo/", {"escudo": png()}).status_code == 403


@pytest.mark.django_db
def test_sin_almacenamiento_conectado_no_se_sube_nada(
    client: Client, equipo: Equipo, settings: Any
) -> None:
    settings.IMAGENES_DISPONIBLES = False
    org = entrar(client, ORGANIZACION)
    respuesta = org.post(f"/clubes/{equipo.club_id}/escudo/", {"escudo": png()}, follow=True)
    assert "Falta conectar el almacenamiento de imágenes" in respuesta.content.decode()
    assert not Club.objects.get(pk=equipo.club_id).escudo


# ---------- Logo del organizador ----------


@pytest.mark.django_db
def test_el_logo_se_sube_en_datos_de_la_escuela(client: Client) -> None:
    org = entrar(client, ORGANIZACION)
    organizador = Organizador.actual()
    datos = {
        "nombre": organizador.nombre,
        "color_primario": organizador.color_primario,
        "color_acento": organizador.color_acento,
        "logo": png("logo.png"),
    }
    org.post("/escuela/", datos)
    assert (Organizador.actual().logo.name or "").startswith("logos/")
    assert "/imagen/logo/" in org.get("/").content.decode()


# ---------- Patrocinadores (P69) ----------


@pytest.mark.django_db
def test_patrocinadores_se_agregan_ordenan_y_sacan(client: Client, torneo: Torneo) -> None:
    org = entrar(client, ORGANIZACION)
    url = f"/torneos/{torneo.pk}/patrocinadores/"
    org.post(url, {"nombre": "Marca Uno", "orden": "2", "imagen": png("uno.png")})
    org.post(url, {"nombre": "Marca Dos", "orden": "1", "imagen": png("dos.png")})
    assert list(torneo.patrocinadores.values_list("nombre", flat=True)) == [
        "Marca Dos",
        "Marca Uno",
    ]
    uno = Patrocinador.objects.get(nombre="Marca Uno")
    org.post(f"/patrocinadores/{uno.pk}/orden/", {"orden": "0"})
    assert torneo.patrocinadores.first() == uno
    html = org.get(url).content.decode()
    assert f"/imagen/patrocinador/{uno.pk}/" in html
    archivo = uno.imagen.name or ""
    org.post(f"/patrocinadores/{uno.pk}/borrar/")
    assert not Patrocinador.objects.filter(pk=uno.pk).exists()
    assert not uno.imagen.storage.exists(archivo)


@pytest.mark.django_db
def test_un_patrocinador_necesita_imagen_y_nombre(client: Client, torneo: Torneo) -> None:
    org = entrar(client, ORGANIZACION)
    org.post(f"/torneos/{torneo.pk}/patrocinadores/", {"nombre": "", "orden": "1"})
    assert not Patrocinador.objects.exists()


@pytest.mark.django_db
def test_la_mesa_no_toca_los_patrocinadores(client: Client, torneo: Torneo) -> None:
    mesa = entrar(client, MESA)
    url = f"/torneos/{torneo.pk}/patrocinadores/"
    assert mesa.get(url).status_code == 403
    assert mesa.post(url, {"nombre": "X", "orden": "1", "imagen": png()}).status_code == 403
