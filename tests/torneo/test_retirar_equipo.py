"""T13.4 (P87, por defecto): retirar un equipo con el torneo empezado. Datos inventados.

Lo jugado cuenta; lo que falta pasa a W.O. 3 a 0 para el rival, con historial.
"""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Partido, Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.clubes import NoSePuede
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.equipos import retirar_equipo
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.tabla import tablas_de


@pytest.fixture
def sub9() -> CategoriaNivel:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    return torneo.categorias.get(categoria="Sub 9", nivel="avanzado")


@pytest.fixture
def equipos(sub9: CategoriaNivel) -> list[Equipo]:
    lista = [
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=sub9, nombre=f"Equipo {i}"
        )
        for i in range(4)
    ]
    generar_fixture(sub9, semilla=1)
    return lista


def entrar(client: Client, rol: str) -> Client:
    usuario = User.objects.create_user(rol[:4], password="x")
    usuario.groups.add(Group.objects.get(name=rol))
    client.force_login(usuario)
    return client


def del_equipo(equipo: Equipo) -> list[Partido]:
    return list(
        Partido.objects.filter(fase=Partido.Fase.GRUPOS)
        .filter(local=equipo)
        .union(Partido.objects.filter(fase=Partido.Fase.GRUPOS, visitante=equipo))
        .order_by("fecha")
    )


@pytest.mark.django_db
def test_lo_jugado_cuenta_y_lo_que_falta_es_wo(sub9: CategoriaNivel, equipos: list[Equipo]) -> None:
    retirado = equipos[0]
    primero, *resto = del_equipo(retirado)
    primero.estado = Partido.Estado.JUGADO
    primero.save()
    retirar_equipo(retirado, usuario=None)
    retirado.refresh_from_db()
    assert retirado.retirado_en is not None
    for partido in resto:
        partido.refresh_from_db()
        assert partido.estado == Partido.Estado.JUGADO
        lado = "local" if partido.local_id == retirado.pk else "visitante"
        assert partido.no_se_presento == lado
        assert partido.registros.filter(que__icontains="retir").exists()
    primero.refresh_from_db()
    assert primero.no_se_presento == ""
    # En la tabla, el retirado tiene sus 3 partidos (1 jugado, 2 por W.O.).
    filas = {f.equipo: f for t in tablas_de(sub9) for f in t.filas}
    assert filas[retirado.pk].pj == 3


@pytest.mark.django_db
def test_un_retirado_no_se_retira_dos_veces(equipos: list[Equipo]) -> None:
    retirar_equipo(equipos[0], usuario=None)
    with pytest.raises(NoSePuede, match="ya se retiró"):
        retirar_equipo(equipos[0], usuario=None)


@pytest.mark.django_db
def test_la_ficha_retira_con_confirmacion(client: Client, equipos: list[Equipo]) -> None:
    equipo = equipos[0]
    org = entrar(client, ORGANIZACION)
    assert (
        f"/equipos/{equipo.pk}/retirar/"
        in org.get(f"/equipos/{equipo.pk}/plantel/").content.decode()
    )
    pide = org.post(f"/equipos/{equipo.pk}/retirar/").content.decode()
    assert "3 partidos" in pide and "W.O." in pide
    org.post(f"/equipos/{equipo.pk}/retirar/", {"confirmado": "1"})
    equipo.refresh_from_db()
    assert equipo.retirado_en is not None
    ficha = org.get(f"/equipos/{equipo.pk}/plantel/").content.decode()
    assert "Retirado" in ficha


@pytest.mark.django_db
def test_posiciones_y_fixture_lo_marcan_retirado(
    client: Client, sub9: CategoriaNivel, equipos: list[Equipo]
) -> None:
    retirar_equipo(equipos[0], usuario=None)
    org = entrar(client, ORGANIZACION)
    assert "Retirado" in org.get(f"/torneo/{sub9.pk}/posiciones/").content.decode()
    assert "Retirado" in org.get(f"/torneo/{sub9.pk}/fixture/").content.decode()


@pytest.mark.django_db
def test_la_mesa_no_retira(client: Client, equipos: list[Equipo]) -> None:
    mesa = entrar(client, MESA)
    respuesta = mesa.post(f"/equipos/{equipos[0].pk}/retirar/", {"confirmado": "1"})
    assert respuesta.status_code == 403
