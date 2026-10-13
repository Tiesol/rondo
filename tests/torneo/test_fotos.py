"""T8.4: foto de la persona y autorización (P66, P67, P75). Fotos inventadas, en memoria.

Son menores: sin la autorización de la familia, la foto no sale en ningún lado público,
aunque esté cargada.
"""

import io
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Jugador, Persona, Profe, Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion


def foto() -> Any:
    salida = io.BytesIO()
    Image.new("RGB", (1200, 1600), (90, 120, 200)).save(salida, "JPEG")
    return SimpleUploadedFile("foto.jpg", salida.getvalue(), content_type="image/jpeg")


@pytest.fixture
def torneo() -> Torneo:
    return cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))


@pytest.fixture
def jugador(torneo: Torneo) -> Jugador:
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    equipo = Equipo.objects.create(
        club=Club.objects.create(nombre="River"), categoria=cn, nombre="River"
    )
    persona = Persona.objects.create(nombres="Nombre", apellidos="Inventado", anio_nacimiento=2017)
    return Jugador.objects.create(persona=persona, equipo=equipo, dorsal=7)


def entrar(client: Client, grupo: str) -> Client:
    usuario = User.objects.create_user(grupo[:4], password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


def url(persona: Persona) -> str:
    return f"/personas/{persona.pk}/foto/"


@pytest.mark.django_db
def test_la_mesa_sube_una_foto_sin_autorizacion_y_no_se_ve_en_publico(
    client: Client, jugador: Jugador, torneo: Torneo
) -> None:
    torneo.publico = True
    torneo.save()
    mesa = entrar(client, MESA)
    mesa.post(url(jugador.persona), {"foto": foto()})
    persona = Persona.objects.get(pk=jugador.persona_id)
    assert (persona.foto.name or "").startswith("fotos/")
    assert not persona.foto_autorizada
    assert mesa.get(f"/imagen/foto/{persona.pk}/").status_code == 200  # adentro, sí
    client.logout()
    assert client.get(f"/imagen/foto/{persona.pk}/").status_code == 404  # afuera, no


@pytest.mark.django_db
def test_con_autorizacion_y_torneo_publico_se_ve_sin_login(
    client: Client, jugador: Jugador, torneo: Torneo
) -> None:
    org = entrar(client, ORGANIZACION)
    org.post(url(jugador.persona), {"foto": foto(), "autorizada": "on"})
    persona = Persona.objects.get(pk=jugador.persona_id)
    assert persona.foto_autorizada
    assert persona.foto_autorizada_por is not None and persona.foto_autorizada_en is not None
    client.logout()
    assert client.get(f"/imagen/foto/{persona.pk}/").status_code == 404  # torneo sin publicar
    torneo.publico = True
    torneo.save()
    assert client.get(f"/imagen/foto/{persona.pk}/").status_code == 200


@pytest.mark.django_db
def test_el_formulario_pregunta_por_la_autorizacion(client: Client, jugador: Jugador) -> None:
    html = entrar(client, MESA).get(url(jugador.persona)).content.decode()
    assert "La familia mandó esta foto para publicarla" in html
    assert (
        f"/personas/{jugador.persona_id}/foto/"
        in client.get(f"/equipos/{jugador.equipo_id}/plantel/").content.decode()
    )


@pytest.mark.django_db
def test_sacar_la_autorizacion_la_oculta(client: Client, jugador: Jugador, torneo: Torneo) -> None:
    torneo.publico = True
    torneo.save()
    org = entrar(client, ORGANIZACION)
    org.post(url(jugador.persona), {"foto": foto(), "autorizada": "on"})
    org.post(url(jugador.persona), {})  # sin la casilla
    persona = Persona.objects.get(pk=jugador.persona_id)
    assert not persona.foto_autorizada and persona.foto
    client.logout()
    assert client.get(f"/imagen/foto/{persona.pk}/").status_code == 404


@pytest.mark.django_db
def test_quitar_la_foto_la_borra_del_almacenamiento(client: Client, jugador: Jugador) -> None:
    org = entrar(client, ORGANIZACION)
    org.post(url(jugador.persona), {"foto": foto(), "autorizada": "on"})
    archivo = Persona.objects.get(pk=jugador.persona_id).foto.name or ""
    org.post(url(jugador.persona), {"quitar": "1"})
    persona = Persona.objects.get(pk=jugador.persona_id)
    assert not persona.foto and not persona.foto_autorizada
    assert not persona.foto.storage.exists(archivo)


@pytest.mark.django_db
def test_tambien_para_los_profes(client: Client, jugador: Jugador) -> None:
    profe = Persona.objects.create(
        nombres="Profe", apellidos="Inventado", clave_documento="7000009"
    )
    Profe.objects.create(persona=profe, equipo=jugador.equipo, rol="entrenador")
    org = entrar(client, ORGANIZACION)
    assert url(profe) in org.get(f"/equipos/{jugador.equipo_id}/cuerpo-tecnico/").content.decode()
    org.post(url(profe), {"foto": foto()})
    assert Persona.objects.get(pk=profe.pk).foto


@pytest.mark.django_db
def test_sin_rol_no_se_suben_fotos(client: Client, jugador: Jugador) -> None:
    client.force_login(User.objects.create_user("nadie", password="x"))
    assert client.post(url(jugador.persona), {"foto": foto()}).status_code == 403
    assert client.get(f"/imagen/foto/{jugador.persona_id}/").status_code == 404
