"""T13.30: al subir un escudo con fondo (un JPG, o un PNG sin transparencia en los bordes), la
app avisa que se va a ver con su recuadro. Imágenes inventadas."""

import io

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image, ImageDraw

from dominio.config import cargar_config
from torneo.models import Club, Equipo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.imagenes import tiene_fondo


def imagen(formato: str, transparente: bool) -> bytes:
    modo = "RGBA" if transparente else "RGB"
    fondo = (0, 0, 0, 0) if transparente else (255, 255, 255)
    dibujo = Image.new(modo, (200, 200), fondo)
    ImageDraw.Draw(dibujo).ellipse((40, 40, 160, 160), fill=(10, 40, 90, 255)[: len(modo)])
    salida = io.BytesIO()
    dibujo.save(salida, formato)
    return salida.getvalue()


def test_detecta_el_fondo() -> None:
    assert tiene_fondo(io.BytesIO(imagen("JPEG", transparente=False)))
    assert tiene_fondo(io.BytesIO(imagen("PNG", transparente=False)))
    assert not tiene_fondo(io.BytesIO(imagen("PNG", transparente=True)))


@pytest.mark.django_db
def test_al_subir_un_escudo_con_fondo_avisa(client: Client) -> None:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    equipo = Equipo.objects.create(
        club=Club.objects.create(nombre="Norte FC"),
        categoria=torneo.categorias.get(categoria="Sub 9", nivel="inicial"),
        nombre="Norte",
    )
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    url = f"/equipos-del-club/{equipo.equipo_de_club_id}/escudo/"
    jpg = SimpleUploadedFile("escudo.jpg", imagen("JPEG", False), content_type="image/jpeg")
    html = client.post(url, {"escudo": jpg}, follow=True).content.decode()
    assert "sube un PNG sin fondo" in html
    png = SimpleUploadedFile("escudo.png", imagen("PNG", True), content_type="image/png")
    html = client.post(url, {"escudo": png}, follow=True).content.decode()
    assert "sube un PNG sin fondo" not in html
