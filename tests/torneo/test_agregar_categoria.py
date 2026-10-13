"""T11.1: agregar una categoría o un nivel a un torneo ya creado. Datos inventados."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.categorias import NoSePuede, agregar_categoria
from torneo.servicios.configuracion import cargar_configuracion


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    # Como un torneo creado con el asistente sin Sub 9 Avanzado ni Sub 15 Femenino.
    torneo.categorias.filter(categoria="Sub 9", nivel="avanzado").delete()
    torneo.categorias.filter(categoria="Sub 15 Femenino").delete()
    return torneo


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


@pytest.mark.django_db
def test_el_nivel_que_falta_sale_de_la_plantilla(torneo: Torneo) -> None:
    nueva = agregar_categoria(torneo, "Sub 9", "avanzado")
    inicial = torneo.categorias.get(categoria="Sub 9", nivel="inicial")
    assert (nueva.edad, nueva.anios_nacimiento) == (inicial.edad, inicial.anios_nacimiento)
    assert nueva.modalidad == "F7"
    assert {c.codigo for c in nueva.canchas.all()} == {"C1", "C2"}


@pytest.mark.django_db
def test_una_categoria_de_la_plantilla_que_no_se_habia_tildado(torneo: Torneo) -> None:
    nueva = agregar_categoria(torneo, "Sub 15 Femenino", "unico")
    assert (nueva.edad, nueva.genero) == (15, "F")
    assert nueva.canchas.exists()


@pytest.mark.django_db
def test_una_categoria_nueva_con_sus_datos(torneo: Torneo) -> None:
    nueva = agregar_categoria(
        torneo, "Sub 20", "unico", modalidad="F11", min_por_tiempo=25, minimo=12, maximo=20
    )
    assert (nueva.edad, nueva.min_por_tiempo, nueva.max_jugadores) == (20, 25, 20)
    # Las canchas, como las otras de F11.
    assert {c.codigo for c in nueva.canchas.all()} == {"C3"}


@pytest.mark.django_db
def test_lo_que_no_se_puede(torneo: Torneo) -> None:
    with pytest.raises(NoSePuede, match="Ya existe"):
        agregar_categoria(torneo, "Sub 9", "inicial")
    with pytest.raises(NoSePuede, match="nivel único"):
        agregar_categoria(torneo, "Sub 5", "avanzado")
    with pytest.raises(NoSePuede, match="Sub"):
        agregar_categoria(torneo, "Veteranos", "unico", modalidad="F7", min_por_tiempo=20)
    with pytest.raises(NoSePuede, match="Completa"):
        agregar_categoria(torneo, "Sub 20", "unico")


@pytest.mark.django_db
def test_desde_la_pantalla(org: Client, torneo: Torneo) -> None:
    otra = torneo.categorias.first()
    assert otra is not None
    html = org.get(f"/torneo/{otra.pk}/equipos/").content.decode()
    assert f"/torneos/{torneo.pk}/categorias/nueva/" in html
    respuesta = org.post(
        f"/torneos/{torneo.pk}/categorias/nueva/", {"nombre": "Sub 9", "nivel": "avanzado"}
    )
    nueva = CategoriaNivel.objects.get(torneo=torneo, categoria="Sub 9", nivel="avanzado")
    assert respuesta.status_code == 302
    assert respuesta["Location"] == f"/torneo/{nueva.pk}/ajustes/"
