"""T11.12 (P82, respondida): un partido olvidado se cierra solo, contando desde el inicio real
del 2.º tiempo. Datos inventados."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Partido, Registro, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios import partido as servicio
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.partido import cerrar_olvidados


@pytest.fixture
def partido() -> Partido:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"E{i}"
        )
    generar_fixture(cn, semilla=1)
    p = cn.partidos.filter(fase="grupos").select_related("categoria__torneo").first()
    assert p is not None
    servicio.empezar(p, None)
    return p


def en_el_segundo_tiempo_desde(partido: Partido, minutos: int) -> None:
    """El 2.º tiempo empezó hace `minutos` (el primero, mucho antes: no importa)."""
    ahora = timezone.now()
    Partido.objects.filter(pk=partido.pk).update(
        tiempo=Partido.Tiempo.SEGUNDO_TIEMPO,
        inicio_real=ahora - timedelta(hours=3),
        fin_primer_tiempo=ahora - timedelta(hours=2),
        fin_descanso=ahora - timedelta(minutes=minutos),
    )
    partido.refresh_from_db()


@pytest.mark.django_db
def test_cuenta_desde_el_inicio_del_segundo_tiempo(partido: Partido) -> None:
    por_tiempo = partido.categoria.min_por_tiempo  # 20 en Sub 9
    # 2.º tiempo empezado hace 20 + 14 minutos: todavía no.
    en_el_segundo_tiempo_desde(partido, por_tiempo + 14)
    assert cerrar_olvidados(partido.categoria.torneo) == 0
    # Hace 20 + 16: se cierra, aunque el inicio del partido fue hace 3 horas.
    en_el_segundo_tiempo_desde(partido, por_tiempo + 16)
    assert cerrar_olvidados(partido.categoria.torneo) == 1
    partido.refresh_from_db()
    assert partido.estado == Partido.Estado.JUGADO
    assert partido.cerrado_automaticamente
    assert Registro.objects.filter(partido=partido, que="Cerrado automáticamente").exists()


@pytest.mark.django_db
def test_sin_segundo_tiempo_cuenta_desde_el_inicio_real(partido: Partido) -> None:
    Partido.objects.filter(pk=partido.pk).update(
        inicio_real=timezone.now() - timedelta(minutes=partido.categoria.minutos_partido + 16)
    )
    assert cerrar_olvidados(partido.categoria.torneo) == 1


@pytest.mark.django_db
def test_los_minutos_salen_de_la_regla(partido: Partido) -> None:
    torneo = partido.categoria.torneo
    torneo.reglas = torneo.reglas | {"cierre_automatico_min": 60}
    torneo.save()
    en_el_segundo_tiempo_desde(partido, partido.categoria.min_por_tiempo + 16)
    assert cerrar_olvidados(torneo) == 0


@pytest.mark.django_db
def test_corre_solo_al_abrir_hoy_y_con_un_comando(client: Client, partido: Partido) -> None:
    en_el_segundo_tiempo_desde(partido, 120)
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    client.get("/hoy/")
    partido.refresh_from_db()
    assert partido.cerrado_automaticamente
    html = client.get(f"/partidos/{partido.pk}/ficha/").content.decode()
    assert "Cerrado automáticamente" in html
    # El comando, para un cron si lo hay.
    otro = Partido.objects.filter(fase="grupos").exclude(pk=partido.pk).first()
    assert otro is not None
    servicio.empezar(otro, None)
    en_el_segundo_tiempo_desde(otro, 120)
    call_command("cerrar_partidos_olvidados")
    otro.refresh_from_db()
    assert otro.estado == Partido.Estado.JUGADO


@pytest.mark.django_db
def test_marcar_como_revisado(client: Client, partido: Partido) -> None:
    en_el_segundo_tiempo_desde(partido, 120)
    cerrar_olvidados(partido.categoria.torneo)
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    client.post(f"/partidos/{partido.pk}/ficha/accion/", {"accion": "revisado"})
    partido.refresh_from_db()
    assert not partido.cerrado_automaticamente
