"""T11.14: la página pública en vivo. Cada 30 s (P73), interruptor de goleadores (P71),
estado "2T 27'" y atraso. Datos inventados."""

from datetime import timedelta
from html import unescape

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Partido, Torneo
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture


@pytest.fixture(autouse=True)
def sin_cache() -> None:
    cache.clear()


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    torneo.publico = True
    torneo.save()
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
    generar_fixture(cn, semilla=1)
    c2 = torneo.canchas.get(codigo="C2")
    ahora = timezone.now().replace(second=0, microsecond=0)
    turno = timedelta(minutes=cn.minutos_turno)
    for i, partido in enumerate(cn.partidos.filter(fase="grupos").order_by("pk")[:2]):
        partido.cancha, partido.inicio = c2, ahora - timedelta(minutes=40) + i * turno
        partido.estado = Partido.Estado.PROGRAMADO
        if i == 0:  # en el 2.º tiempo, que empezó hace 6 minutos (y tarde)
            partido.estado, partido.tiempo = Partido.Estado.EN_JUEGO, Partido.Tiempo.SEGUNDO_TIEMPO
            partido.inicio_real = ahora - timedelta(minutes=30)
            partido.fin_primer_tiempo = ahora - timedelta(minutes=10)
            partido.fin_descanso = ahora - timedelta(minutes=6)
        partido.save()
    return torneo


@pytest.mark.django_db
def test_se_recarga_cada_30_segundos(client: Client, torneo: Torneo) -> None:
    html = client.get(f"/t/{torneo.pk}/hoy/").content.decode()
    assert 'hx-trigger="every 30s"' in html


@pytest.mark.django_db
def test_estado_con_el_minuto_y_el_atraso(client: Client, torneo: Torneo) -> None:
    html = unescape(client.get(f"/t/{torneo.pk}/hoy/").content.decode())
    assert "2T 27'" in html  # 20 del primero + el 7.º del segundo
    assert "min tarde" in html


@pytest.mark.django_db
def test_sin_goleadores_si_el_torneo_lo_apaga(client: Client, torneo: Torneo) -> None:
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    url = f"/t/{torneo.pk}/{cn.pk}/partidos/"
    assert "Goleadores" in client.get(url).content.decode()
    torneo.reglas = torneo.reglas | {"tabla_de_goleadores": False}
    torneo.save()
    cache.clear()
    assert "Goleadores" not in client.get(url).content.decode()
    assert client.get(f"/t/{torneo.pk}/{cn.pk}/goleadores/").status_code == 404
