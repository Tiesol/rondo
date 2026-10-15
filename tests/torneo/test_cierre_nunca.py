"""T13.11 (P82: "no se cierra sola"): por defecto, un partido olvidado sigue en juego y Hoy y
la ficha avisan que pasó su final. Datos inventados."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import Reglas, cargar_config
from torneo.models import Club, Equipo, Partido, Torneo
from torneo.permisos import MESA
from torneo.servicios import partido as servicio
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.partido import cerrar_olvidados


@pytest.fixture
def olvidado() -> Partido:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"E{i}"
        )
    generar_fixture(cn, semilla=1)
    p = cn.partidos.filter(fase="grupos").select_related("categoria__torneo").first()
    assert p is not None
    ahora = timezone.now()
    cancha = cn.canchas.first()
    Partido.objects.filter(pk=p.pk).update(inicio=ahora - timedelta(hours=3), cancha=cancha)
    p.refresh_from_db()
    servicio.empezar(p, None)
    Partido.objects.filter(pk=p.pk).update(inicio_real=ahora - timedelta(hours=3))
    p.refresh_from_db()
    return p


def test_la_regla_viene_apagada() -> None:
    assert Reglas().cierre_automatico is False
    assert cargar_config(settings.PLANTILLA_TORNEO).reglas.cierre_automatico is False


@pytest.mark.django_db
def test_por_defecto_no_se_cierra_solo(olvidado: Partido) -> None:
    assert cerrar_olvidados(olvidado.categoria.torneo) == 0
    olvidado.refresh_from_db()
    assert olvidado.estado == Partido.Estado.EN_JUEGO


@pytest.mark.django_db
def test_hoy_y_la_ficha_avisan_que_sigue_abierto(client: Client, olvidado: Partido) -> None:
    usuario = User.objects.create_user("mesa", password="x")
    usuario.groups.add(Group.objects.get(name=MESA))
    client.force_login(usuario)
    fin = timezone.localtime(servicio.fin_esperado(olvidado)).strftime("%H:%M")
    dia = timezone.localtime(olvidado.inicio).date().isoformat()
    hoy = client.get(f"/hoy/?dia={dia}").content.decode()
    assert f"Sigue abierto (terminaba {fin})" in hoy
    ficha = client.get(f"/partidos/{olvidado.pk}/ficha/").content.decode()
    assert f"pasó su final ({fin})" in ficha
