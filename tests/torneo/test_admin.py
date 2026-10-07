"""T1.5: admin de la configuración e identidad del organizador."""

from datetime import date

import pytest
from django.contrib.admin.sites import site
from django.contrib.auth.models import User
from django.test import Client, RequestFactory

from torneo.models import CategoriaNivel, Organizador, Torneo


def _torneo() -> Torneo:
    return Torneo.objects.create(
        nombre="JMP CUP 2026",
        edicion=5,
        anio=2026,
        inicio=date(2026, 10, 23),
        fin=date(2026, 11, 22),
    )


@pytest.mark.django_db
def test_alguien_sin_staff_no_entra_al_admin(client: Client) -> None:
    client.force_login(User.objects.create_user("mesa", password="x"))
    assert client.get("/admin/").status_code == 302


@pytest.mark.django_db
def test_el_organizador_edita_un_tope_de_jugadores(client: Client) -> None:
    client.force_login(User.objects.create_superuser("sebastian", password="x"))
    sub9 = CategoriaNivel.objects.create(
        torneo=_torneo(),
        categoria="Sub 9",
        edad=9,
        nivel="inicial",
        modalidad="F7",
        min_jugadores=12,
        max_jugadores=14,
        min_por_tiempo=20,
    )
    url = f"/admin/torneo/categorianivel/{sub9.pk}/change/"
    assert client.get(url).status_code == 200

    datos = {
        "torneo": sub9.torneo.pk,
        "categoria": "Sub 9",
        "edad": 9,
        "anios_nacimiento": 1,
        "genero": "mixto",
        "nivel": "inicial",
        "modalidad": "F7",
        "min_jugadores": 12,
        "max_jugadores": 15,
        "min_por_tiempo": 20,
        "convocados_por_partido": "",
    }
    respuesta = client.post(url, datos)

    assert respuesta.status_code == 302, respuesta.content.decode()[:2000]
    sub9.refresh_from_db()
    assert sub9.max_jugadores == 15


@pytest.mark.django_db
def test_una_regla_invalida_muestra_el_error_junto_al_campo() -> None:
    torneo = _torneo()
    admin = site._registry[Torneo]
    pedido = RequestFactory().get("/")
    pedido.user = User.objects.create_superuser("sebastian", password="x")
    formulario_clase = admin.get_form(pedido, torneo)
    datos = {
        campo: getattr(torneo, campo)
        for campo in (
            "nombre",
            "edicion",
            "anio",
            "inicio",
            "fin",
            "zona_horaria",
            "descanso_min",
            "cambio_entre_partidos_min",
        )
    }
    datos |= {
        "cuerpo_tecnico": '{"max_por_equipo": 3}',
        "reglas": '{"max_partidos_por_dia": "dos"}',
    }

    formulario = formulario_clase(datos, instance=torneo)

    assert not formulario.is_valid()
    assert "max_partidos_por_dia" in str(formulario.errors["reglas"])


@pytest.mark.django_db
def test_hay_un_solo_organizador_y_tiene_valores_por_defecto() -> None:
    primero = Organizador.actual()
    assert Organizador.actual().pk == primero.pk
    assert Organizador.objects.count() == 1
    assert primero.nombre


@pytest.mark.django_db
def test_el_nombre_del_organizador_aparece_en_las_pantallas(client: Client) -> None:
    organizador = Organizador.actual()
    organizador.nombre = "Escuela de Prueba"
    organizador.save()
    html = client.get("/cuentas/login/").content.decode()
    assert "Escuela de Prueba" in html
    assert "JMP" not in html


@pytest.mark.django_db
def test_el_color_del_organizador_tiene_que_ser_hexadecimal() -> None:
    from django.core.exceptions import ValidationError

    organizador = Organizador.actual()
    organizador.color_primario = "verde"
    with pytest.raises(ValidationError):
        organizador.full_clean()
