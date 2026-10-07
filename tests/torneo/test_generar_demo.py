"""T2.7: generador de datos de demo. Todo inventado, con semilla fija."""

import io
from collections import Counter
from datetime import date

import pytest
from django.core.management import CommandError, call_command
from django.db.models import Count

from dominio.config import CuerpoTecnico, Reglas
from torneo.models import Club, Equipo, Jugador, Persona, Profe, Torneo


def generar() -> str:
    salida = io.StringIO()
    call_command("generar_demo", "--soy-la-demo", stdout=salida)
    return salida.getvalue()


@pytest.mark.django_db
def test_sin_la_bandera_no_hace_nada() -> None:
    salida = io.StringIO()
    call_command("generar_demo", stdout=salida)
    assert "--soy-la-demo" in salida.getvalue()
    assert not Torneo.objects.exists()
    assert not Equipo.objects.exists()


@pytest.fixture
def demo(db: None) -> Torneo:
    generar()
    return Torneo.objects.get(es_demo=True)


def test_arma_un_torneo_del_tamanio_de_2023(demo: Torneo) -> None:
    equipos = Equipo.objects.filter(categoria__torneo=demo)
    assert 80 <= equipos.count() <= 100
    assert demo.publico
    assert Club.objects.filter(nombre="JMP").exists()
    assert equipos.filter(club__nombre="JMP", nombre="JMP Academy").exists()
    assert equipos.filter(categoria__categoria="Sub 15 Femenino").exists()


def test_los_planteles_respetan_los_topes(demo: Torneo) -> None:
    cortos = 0
    for equipo in Equipo.objects.select_related("categoria").annotate(n=Count("jugadores")):
        assert equipo.n <= equipo.categoria.max_jugadores, equipo
        cortos += equipo.n < equipo.categoria.min_jugadores
    assert 1 <= cortos <= 5


def test_nadie_es_mayor_que_su_categoria(demo: Torneo) -> None:
    for jugador in Jugador.objects.select_related("persona", "equipo__categoria"):
        categoria = jugador.equipo.categoria
        primero = demo.anio - categoria.edad
        assert jugador.persona.nacimiento is not None
        assert jugador.persona.nacimiento.year >= primero, jugador


def test_hay_casos_para_ver_los_avisos(demo: Torneo) -> None:
    reglas = Reglas.model_validate(demo.reglas)
    jugadores = Jugador.objects.select_related("persona", "equipo__categoria")
    assert jugadores.filter(persona__clave_documento="").exists()
    assert jugadores.filter(dorsal__isnull=True).exists()
    muy_chicos = [
        j
        for j in jugadores
        if j.persona.nacimiento
        and j.persona.nacimiento.year
        - (demo.anio - j.equipo.categoria.edad + j.equipo.categoria.anios_nacimiento - 1)
        > reglas.aviso_anios_menor
    ]
    assert muy_chicos


def test_los_7_jugadores_compartidos_de_6_4(demo: Torneo) -> None:
    compartidos = Persona.objects.annotate(n=Count("jugadores")).filter(n__gt=1)
    assert compartidos.count() == 7
    for persona in compartidos:
        equipos = [
            j.equipo for j in persona.jugadores.select_related("equipo__club", "equipo__categoria")
        ]
        assert len({e.club_id for e in equipos}) == 1, "mismo club"
        assert len({e.categoria.categoria for e in equipos}) == len(equipos), "otra categoría"
    clubes = Counter(
        p.jugadores.first().equipo.club.nombre  # type: ignore[union-attr]
        for p in compartidos
    )
    assert clubes == {"Inter Star": 4, "River Plate": 3}


def test_los_profes_compartidos_de_6_4_y_el_cuerpo_tecnico(demo: Torneo) -> None:
    cuerpo = CuerpoTecnico.model_validate(demo.cuerpo_tecnico)
    for equipo in Equipo.objects.prefetch_related("profes"):
        roles = [p.rol for p in equipo.profes.all()]
        assert 1 <= len(roles) <= cuerpo.max_por_equipo, equipo
        assert roles.count("entrenador") == 1, equipo
        assert set(roles) <= set(cuerpo.roles)
    compartidos = Persona.objects.annotate(n=Count("profes")).filter(n__gt=1)
    assert compartidos.count() == 17  # 18 en 6.4, menos el par de Crack FC (REVISAR R35)
    river = [
        p
        for p in compartidos
        if p.profes.first().equipo.club.nombre == "River Plate"  # type: ignore[union-attr]
    ]
    assert len(river) == 7


def test_correrlo_dos_veces_no_duplica(demo: Torneo) -> None:
    antes = (Equipo.objects.count(), Jugador.objects.count(), Profe.objects.count())
    claves = set(Persona.objects.values_list("clave_documento", flat=True))
    generar()
    assert (Equipo.objects.count(), Jugador.objects.count(), Profe.objects.count()) == antes
    assert set(Persona.objects.values_list("clave_documento", flat=True)) == claves
    assert Torneo.objects.count() == 1


@pytest.mark.django_db
def test_se_niega_si_hay_datos_que_no_son_de_demo() -> None:
    real = Torneo.objects.create(
        nombre="Real", edicion=1, anio=2026, inicio=date(2026, 10, 1), fin=date(2026, 11, 1)
    )
    from torneo.models import CategoriaNivel

    categoria = CategoriaNivel.objects.create(
        torneo=real,
        categoria="Sub 9",
        edad=9,
        nivel="unico",
        modalidad="F7",
        min_jugadores=1,
        max_jugadores=2,
        min_por_tiempo=10,
    )
    Equipo.objects.create(club=Club.objects.create(nombre="X"), categoria=categoria, nombre="X")
    with pytest.raises(CommandError, match="no son de demo"):
        generar()
    assert Equipo.objects.count() == 1
