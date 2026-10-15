"""T13.22: editar los cruces del fixture a mano.

Dos operaciones, las dos por fecha (en un todos contra todos, cambiar un cruce suelto siempre
deja a alguien dos veces en la fecha): "Rearmar la fecha", eligiendo los equipos de todos sus
cruces a la vez, e "Intercambiar con otra fecha". Bloquea: un equipo dos veces en una fecha y un
cruce que el formato no tiene. Avisa, sin bloquear: a quién le falta jugar con quién y qué
cruce se repite. Datos inventados.
"""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Partido, Registro, Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.clubes import NoSePuede
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.cruces_a_mano import avisos_del_fixture, intercambiar_fechas, rearmar_fecha
from torneo.servicios.fixture import generar_fixture


def categoria_con(cuantos: int) -> tuple[CategoriaNivel, dict[str, Equipo]]:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="inicial")
    equipos = {
        letra: Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {letra}"), categoria=cn, nombre=letra
        )
        for letra in "ABCDEFGH"[:cuantos]
    }
    generar_fixture(cn, semilla=1)
    return cn, equipos


def de_la_fecha(cn: CategoriaNivel, fecha: int) -> list[Partido]:
    return list(cn.partidos.filter(fase="grupos", fecha=fecha).order_by("pk"))


def cruces(cn: CategoriaNivel, fecha: int) -> set[frozenset[str]]:
    return {
        frozenset((p.local.nombre, p.visitante.nombre))  # type: ignore[union-attr]
        for p in cn.partidos.filter(fase="grupos", fecha=fecha).select_related("local", "visitante")
    }


def fecha_de(cn: CategoriaNivel, a: Equipo, b: Equipo) -> int:
    for p in cn.partidos.filter(fase="grupos"):
        if {p.local_id, p.visitante_id} == {a.pk, b.pk}:
            assert p.fecha is not None
            return p.fecha
    raise AssertionError("no juegan")


@pytest.mark.django_db
def test_adelantar_un_cruce_a_la_fecha_1_rearmando_las_dos_fechas() -> None:
    """El ejemplo de Sebastian: si la fecha 1 tiene A-B y C-D, y la otra fecha tiene A-D y
    B-C, se puede adelantar A-D a la fecha 1."""
    cn, e = categoria_con(4)
    otra = fecha_de(cn, e["A"], e["D"])
    uno = fecha_de(cn, e["A"], e["B"])
    assert otra != uno
    f_uno, f_otra = de_la_fecha(cn, uno), de_la_fecha(cn, otra)
    rearmar_fecha(cn, uno, {f_uno[0].pk: (e["A"], e["D"]), f_uno[1].pk: (e["B"], e["C"])}, None)
    # Mientras la otra fecha no se rearma, A-D se repite: avisa, no bloquea.
    assert any("A vs D está repetido" in a for a in avisos_del_fixture(cn))
    rearmar_fecha(cn, otra, {f_otra[0].pk: (e["A"], e["B"]), f_otra[1].pk: (e["C"], e["D"])}, None)
    assert cruces(cn, uno) == {frozenset("AD"), frozenset("BC")}
    assert avisos_del_fixture(cn) == []
    assert all(p.editado_a_mano for p in de_la_fecha(cn, uno))
    assert Registro.objects.filter(que="Cruce cambiado a mano").exists()


@pytest.mark.django_db
def test_un_equipo_dos_veces_en_la_fecha_bloquea() -> None:
    cn, e = categoria_con(4)
    f1 = de_la_fecha(cn, 1)
    with pytest.raises(NoSePuede, match="A juega dos partidos en la fecha 1"):
        rearmar_fecha(cn, 1, {f1[0].pk: (e["A"], e["B"]), f1[1].pk: (e["A"], e["C"])}, None)
    assert not cn.partidos.filter(editado_a_mano=True).exists()


@pytest.mark.django_db
def test_lo_que_falta_se_avisa() -> None:
    cn, e = categoria_con(4)
    uno = fecha_de(cn, e["A"], e["B"])
    otra = fecha_de(cn, e["A"], e["C"])
    f = de_la_fecha(cn, otra)
    rearmar_fecha(cn, otra, {f[0].pk: (e["A"], e["B"]), f[1].pk: (e["C"], e["D"])}, None)
    avisos = avisos_del_fixture(cn)
    assert any("A vs B está repetido" in a for a in avisos)
    assert any("A todavía no juega con C" in a for a in avisos)
    assert uno != otra


@pytest.mark.django_db
def test_en_series_cruzadas_no_se_arma_un_cruce_de_la_misma_serie() -> None:
    cn, _ = categoria_con(6)
    a1, a2, a3 = cn.series.get(nombre="A").equipos.order_by("pk")
    b1, b2, b3 = cn.series.get(nombre="B").equipos.order_by("pk")
    f1 = de_la_fecha(cn, 1)
    with pytest.raises(NoSePuede, match="misma serie"):
        rearmar_fecha(cn, 1, {f1[0].pk: (a1, a2), f1[1].pk: (b1, b2), f1[2].pk: (a3, b3)}, None)


@pytest.mark.django_db
def test_intercambiar_dos_fechas() -> None:
    cn, _ = categoria_con(4)
    antes_1, antes_2 = cruces(cn, 1), cruces(cn, 2)
    intercambiar_fechas(cn, 1, 2, None)
    assert (cruces(cn, 1), cruces(cn, 2)) == (antes_2, antes_1)
    assert avisos_del_fixture(cn) == []


@pytest.mark.django_db
def test_una_fecha_con_un_partido_jugado_no_se_rearma() -> None:
    cn, _ = categoria_con(4)
    f1 = de_la_fecha(cn, 1)
    Partido.objects.filter(pk=f1[0].pk).update(estado=Partido.Estado.JUGADO)
    with pytest.raises(NoSePuede, match="ya se jugó"):
        rearmar_fecha(cn, 1, {f1[0].pk: (f1[0].visitante, f1[0].local)}, None)
    with pytest.raises(NoSePuede, match="ya se jugó"):
        intercambiar_fechas(cn, 1, 2, None)


@pytest.mark.django_db
def test_la_pantalla_de_la_fecha(client: Client) -> None:
    cn, _ = categoria_con(4)
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    url = f"/torneo/{cn.pk}/fecha/1/"
    assert url in client.get(f"/torneo/{cn.pk}/fixture/").content.decode()
    html = client.get(url).content.decode()
    assert "Guardar la fecha" in html and "Intercambiar con la fecha" in html
    f1 = de_la_fecha(cn, 1)
    datos = {"accion": "rearmar"}
    for p in f1:
        datos |= {f"local_{p.pk}": str(p.visitante_id), f"visitante_{p.pk}": str(p.local_id)}
    assert client.post(url, datos).status_code == 302
    assert all(p.editado_a_mano for p in de_la_fecha(cn, 1))
    assert client.post(url, {"accion": "intercambiar", "otra": "2"}).status_code == 302


@pytest.mark.django_db
def test_la_mesa_no_edita_cruces(client: Client) -> None:
    cn, _ = categoria_con(4)
    usuario = User.objects.create_user("mesa", password="x")
    usuario.groups.add(Group.objects.get(name=MESA))
    client.force_login(usuario)
    assert client.get(f"/torneo/{cn.pk}/fecha/1/").status_code == 403
