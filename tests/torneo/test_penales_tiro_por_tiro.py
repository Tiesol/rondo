"""T11.13 (P83): penales tiro por tiro desde la ficha, y el atajo del resultado final.
Datos inventados."""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Partido, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios import partido as servicio
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture


@pytest.fixture
def final() -> Partido:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    equipos = [
        Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"E{i}"
        )
        for i in range(4)
    ]
    generar_fixture(cn, semilla=1)
    partido = cn.partidos.filter(fase="eliminacion").first()
    assert partido is not None
    partido.local, partido.visitante = equipos[0], equipos[1]
    partido.save()
    servicio.empezar(partido, None)
    return partido


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


def patear(org: Client, partido: Partido, equipo: Equipo | None, convirtio: bool) -> None:
    assert equipo is not None
    org.post(
        f"/partidos/{partido.pk}/ficha/accion/",
        {"accion": "penal", "equipo": equipo.pk, "convirtio": "1" if convirtio else ""},
    )


@pytest.mark.django_db
def test_una_tanda_completa_desde_la_ficha(org: Client, final: Partido) -> None:
    html = org.get(f"/partidos/{final.pk}/ficha/").content.decode()
    assert "Convirtió" in html and "Falló" in html
    for local, visitante in [(True, True), (True, True), (True, False)]:
        patear(org, final, final.local, local)
        patear(org, final, final.visitante, visitante)
    resultado = servicio.resultado_de(final)
    assert resultado.penales == (3, 2)
    assert resultado.ganador == "local"
    servicio.terminar(final, None)
    # Con ganador, no se patea más.
    with pytest.raises(servicio.NoSePuede):
        servicio.patear(final, final.visitante, True, None)  # type: ignore[arg-type]


@pytest.mark.django_db
def test_deshacer_el_ultimo_penal(org: Client, final: Partido) -> None:
    patear(org, final, final.local, True)
    org.post(f"/partidos/{final.pk}/ficha/accion/", {"accion": "deshacer_penal"})
    assert not final.tiros.exists()


@pytest.mark.django_db
def test_los_penales_por_equipo_salen_de_la_regla(final: Partido) -> None:
    torneo = final.categoria.torneo
    torneo.reglas = torneo.reglas | {"penales_por_equipo": 5}
    torneo.save()
    for _ in range(3):
        servicio.patear(final, final.local, True, None)  # type: ignore[arg-type]
        servicio.patear(final, final.visitante, False, None)  # type: ignore[arg-type]
    assert servicio.resultado_de(final).ganador == "local"  # 3 a 0 con 2 por patear: ya no llega
    final.tiros.all().delete()
    for _ in range(3):
        servicio.patear(final, final.local, True, None)  # type: ignore[arg-type]
        servicio.patear(final, final.visitante, True, None)  # type: ignore[arg-type]
    assert servicio.resultado_de(final).ganador is None  # con 5 por equipo, sigue


@pytest.mark.django_db
def test_el_atajo_carga_solo_el_resultado(org: Client, final: Partido) -> None:
    org.post(
        f"/partidos/{final.pk}/ficha/accion/", {"accion": "penales", "local": 4, "visitante": 3}
    )
    final.refresh_from_db()
    assert servicio.resultado_de(final).penales == (4, 3)
