"""Revisión de seguridad de la fase 8: imágenes, página pública en caché y ficha del partido."""

import io

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Club, EquipoDeClub, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.imagenes import ImagenInvalida, procesar_imagen

SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


def test_un_svg_con_script_no_pasa_como_imagen() -> None:
    with pytest.raises(ImagenInvalida):
        procesar_imagen(io.BytesIO(SVG), tipo="escudo")


@pytest.mark.django_db
def test_un_svg_subido_como_escudo_no_se_guarda(client: Client) -> None:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    del_club = EquipoDeClub.objects.create(club=Club.objects.create(nombre="Club"), nombre="Club")
    falso = SimpleUploadedFile("escudo.png", SVG, content_type="image/png")
    client.post(f"/equipos-del-club/{del_club.pk}/escudo/", {"escudo": falso})
    assert not EquipoDeClub.objects.get(pk=del_club.pk).escudo


@pytest.mark.django_db
def test_un_aviso_de_la_organizacion_no_queda_en_la_cache_publica() -> None:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    torneo.publico = True
    torneo.save()
    categoria = torneo.categorias.first()
    assert categoria is not None
    pagina = f"/t/{torneo.pk}/{categoria.pk}/partidos/"

    org = Client()
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    org.force_login(usuario)
    club = Club.objects.create(nombre="Club Secreto Inventado")
    del_club = EquipoDeClub.objects.create(club=club, nombre=club.nombre)
    org.post(f"/equipos-del-club/{del_club.pk}/escudo/", {})  # deja un aviso pendiente en su sesión
    assert "Elige la imagen del escudo" not in org.get(pagina).content.decode()
    anonimo = Client()
    respuesta = anonimo.get(pagina)
    assert "Elige la imagen del escudo" not in respuesta.content.decode()
    assert "csrftoken" not in respuesta.cookies  # sin cookies: la caché se comparte
    # El aviso queda para la próxima pantalla interna de quien lo generó.
    assert "Elige la imagen del escudo" in org.get("/").content.decode()


@pytest.mark.django_db
def test_un_tipo_de_imagen_inventado_da_404(client: Client) -> None:
    assert client.get("/imagen/persona/1/").status_code == 404
    assert client.get("/imagen/foto/999999/").status_code == 404
