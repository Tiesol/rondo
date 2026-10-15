"""T13.24 (P30): "Copas por club". Por club, cuántas Copas de Oro y de Plata ganó (campeón) y
en cuántas fue subcampeón, con las categorías. Sale solo de las finales jugadas. Datos
inventados."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Evento, Partido, Torneo
from torneo.permisos import MESA
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.copas import copas_por_club
from torneo.servicios.fixture import generar_fixture


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    norte, sur = Club.objects.create(nombre="Norte FC"), Club.objects.create(nombre="Sur FC")
    for categoria in ("Sub 9", "Sub 10"):
        cn: CategoriaNivel = torneo.categorias.get(categoria=categoria, nivel="inicial")
        for i, club in enumerate((norte, sur, norte, sur)):
            Equipo.objects.create(club=club, categoria=cn, nombre=f"{club.nombre[:-3]} {i}")
        generar_fixture(cn, semilla=1)
    return torneo


def jugar_final(cn: CategoriaNivel, copa: str, gana: str) -> None:
    """La final de esa copa: gana el equipo de ese club, 1 a 0."""
    final = cn.partidos.get(fase="eliminacion", copa=copa, ronda="final")
    del_club = cn.equipos.filter(club__nombre=gana).order_by("pk")
    otros = cn.equipos.exclude(club__nombre=gana).order_by("pk")
    final.local, final.visitante = del_club.first(), otros.first()
    final.estado = Partido.Estado.JUGADO
    final.save()
    assert final.local is not None
    Evento.objects.create(partido=final, tipo="gol", equipo=final.local)


@pytest.mark.django_db
def test_cuenta_campeones_y_subcampeones_por_club(torneo: Torneo) -> None:
    sub9 = torneo.categorias.get(categoria="Sub 9", nivel="inicial")
    sub10 = torneo.categorias.get(categoria="Sub 10", nivel="inicial")
    jugar_final(sub9, "oro", "Norte FC")
    jugar_final(sub9, "plata", "Sur FC")
    jugar_final(sub10, "oro", "Norte FC")
    filas = {f.club: f for f in copas_por_club(torneo)}
    norte, sur = filas["Norte FC"], filas["Sur FC"]
    assert norte.oro == ["Sub 9 Inicial", "Sub 10 Inicial"] and norte.plata == []
    assert norte.subcampeon_plata == ["Sub 9 Inicial"]
    assert sur.plata == ["Sub 9 Inicial"]
    assert sur.subcampeon_oro == ["Sub 9 Inicial", "Sub 10 Inicial"]
    # Ordenado por copas de oro.
    assert copas_por_club(torneo)[0].club == "Norte FC"


@pytest.mark.django_db
def test_sin_finales_jugadas_no_hay_nada(torneo: Torneo) -> None:
    assert copas_por_club(torneo) == []


@pytest.mark.django_db
def test_la_pantalla_interna_y_la_publica(client: Client, torneo: Torneo) -> None:
    jugar_final(torneo.categorias.get(categoria="Sub 9", nivel="inicial"), "oro", "Norte FC")
    usuario = User.objects.create_user("mesa", password="x")
    usuario.groups.add(Group.objects.get(name=MESA))
    client.force_login(usuario)
    assert f"/torneos/{torneo.pk}/copas/" in client.get("/mas/").content.decode()
    html = client.get(f"/torneos/{torneo.pk}/copas/").content.decode()
    assert "Norte FC" in html and "Copa de Oro" in html
    client.logout()
    assert client.get(f"/t/{torneo.pk}/copas/").status_code == 404  # sin publicar
    torneo.publico = True
    torneo.save()
    publica = client.get(f"/t/{torneo.pk}/copas/").content.decode()
    assert "Norte FC" in publica and "Sub 9 Inicial" in publica
