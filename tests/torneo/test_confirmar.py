"""B7 (fase 12): un solo "¿Estás seguro?" que dice qué va a pasar."""

import pytest
from django.contrib.auth.models import Group, User
from django.test import Client, RequestFactory

from torneo.permisos import ORGANIZACION
from torneo.views.confirmar import confirmado, pedir_confirmacion


@pytest.mark.django_db
def test_la_pantalla_dice_que_va_a_pasar_y_guarda_los_datos() -> None:
    pedido = RequestFactory().post("/algo/", {"dia": "2026-10-31", "canchas": ["1", "2"]})
    pedido.htmx = False  # type: ignore[attr-defined]
    pedido.user = User.objects.create_user("quien", password="x")
    respuesta = pedir_confirmacion(
        pedido,
        mensaje="Se suspenden los 26 partidos del sábado 31/10.",
        detalle=["3 en juego"],
        boton="Suspender",
    )
    html = respuesta.content.decode()
    assert "Se suspenden los 26 partidos" in html and "Suspender" in html
    assert 'name="dia" value="2026-10-31"' in html
    assert html.count('name="canchas"') == 2
    assert 'name="confirmado" value="1"' in html
    assert not confirmado(pedido)
    assert confirmado(RequestFactory().post("/algo/", {"confirmado": "1"}))


# ---------- B7 desde las pantallas: nada importante se hace con un solo toque ----------


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


@pytest.mark.django_db
def test_publicar_y_despublicar_piden_confirmar(org: Client) -> None:
    from django.conf import settings

    from dominio.config import cargar_config
    from torneo.servicios.configuracion import cargar_configuracion

    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    respuesta = org.post(f"/torneos/{torneo.pk}/publico/")
    assert "se va a ver sin login" in respuesta.content.decode()
    torneo.refresh_from_db()
    assert not torneo.publico
    org.post(f"/torneos/{torneo.pk}/publico/", {"confirmado": "1"})
    torneo.refresh_from_db()
    assert torneo.publico
    assert "deja de verse" in org.post(f"/torneos/{torneo.pk}/publico/").content.decode()


@pytest.mark.django_db
def test_rehacer_un_fixture_dice_cuantos_partidos_se_borran(org: Client) -> None:
    from django.conf import settings

    from dominio.config import cargar_config
    from torneo.models import Club, Equipo
    from torneo.servicios.configuracion import cargar_configuracion
    from torneo.servicios.fixture import generar_fixture

    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"E{i}"
        )
    generar_fixture(cn, semilla=1)
    antes = list(cn.partidos.values_list("pk", flat=True))
    respuesta = org.post(f"/torneo/{cn.pk}/fixture/generar/")
    assert f"se borran sus {len(antes)} partidos" in respuesta.content.decode()
    assert list(cn.partidos.values_list("pk", flat=True)) == antes
