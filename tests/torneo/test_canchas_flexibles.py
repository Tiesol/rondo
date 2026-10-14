"""T10.5: canchas flexibles (P13, P63): agregar canchas y partir cualquiera en mitades."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Cancha, Partido, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.programador import partidos_del_torneo, problema_del_torneo


@pytest.fixture
def torneo() -> Torneo:
    return cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


def url(torneo: Torneo, que: str = "") -> str:
    return f"/torneos/{torneo.pk}/canchas/{que}"


@pytest.mark.django_db
def test_la_pantalla_lista_las_canchas_con_sus_mitades(org: Client, torneo: Torneo) -> None:
    html = org.get(url(torneo)).content.decode()
    for texto in ("Cancha 1", "C1A", "C1B", "Cancha 2", "Cancha 3"):
        assert texto in html


@pytest.mark.django_db
def test_agregar_una_cancha(org: Client, torneo: Torneo) -> None:
    org.post(url(torneo, "agregar/"))
    nueva = Cancha.objects.get(torneo=torneo, codigo="C4")
    assert nueva.nombre == "Cancha 4" and nueva.padre is None
    # Aparece para elegirla en los ajustes de una categoría.
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    assert "C4" in org.get(f"/torneo/{cn.pk}/ajustes/").content.decode()


@pytest.mark.django_db
def test_partir_la_cancha_2_en_mitades(org: Client, torneo: Torneo) -> None:
    c2 = Cancha.objects.get(torneo=torneo, codigo="C2")
    org.post(url(torneo, f"{c2.pk}/partir/"))
    assert set(c2.mitades.values_list("codigo", flat=True)) == {"C2A", "C2B"}
    problema = problema_del_torneo(torneo, partidos_del_torneo(torneo))
    assert problema.fisicas["C2"] == {"C2A", "C2B"}  # la entera ocupa sus dos mitades
    assert problema.fisicas["C2A"] == {"C2A"}


@pytest.mark.django_db
def test_unir_se_niega_si_una_mitad_tiene_partidos(org: Client, torneo: Torneo) -> None:
    c1a = Cancha.objects.get(torneo=torneo, codigo="C1A")
    cn = torneo.categorias.get(categoria="Sub 5", nivel="unico")
    Partido.objects.create(categoria=cn, fase="grupos", fecha=1, cancha=c1a)
    c1 = Cancha.objects.get(torneo=torneo, codigo="C1")
    respuesta = org.post(url(torneo, f"{c1.pk}/unir/"), {"confirmado": "1"}, follow=True)
    assert "tiene partidos" in respuesta.content.decode()
    assert c1.mitades.count() == 2
    Partido.objects.all().delete()
    org.post(url(torneo, f"{c1.pk}/unir/"), {"confirmado": "1"})
    assert c1.mitades.count() == 0


@pytest.mark.django_db
def test_quitar_una_cancha_sin_partidos(org: Client, torneo: Torneo) -> None:
    org.post(url(torneo, "agregar/"))
    c4 = Cancha.objects.get(torneo=torneo, codigo="C4")
    org.post(url(torneo, f"{c4.pk}/quitar/"), {"confirmado": "1"})
    assert not Cancha.objects.filter(pk=c4.pk).exists()


@pytest.mark.django_db
def test_sin_rol_no_se_tocan_las_canchas(client: Client, torneo: Torneo) -> None:
    client.force_login(User.objects.create_user("nadie", password="x"))
    assert client.post(url(torneo, "agregar/")).status_code == 403
