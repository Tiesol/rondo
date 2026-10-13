"""T4.1: pares de equipos que no pueden jugar a la vez, calculados desde Persona."""

import io
from collections import Counter
from dataclasses import fields
from datetime import date

import pytest
from django.conf import settings
from django.core.management import call_command

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Jugador, Persona, Profe, Torneo
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.personas import pares_de_equipos


def test_la_demo_da_los_pares_de_6_4(db: None) -> None:
    call_command("generar_demo", "--soy-la-demo", stdout=io.StringIO())
    torneo = Torneo.objects.get(es_demo=True)
    river = {e.pk for e in Equipo.objects.filter(club__nombre="River Plate")}
    # Con todo el cuerpo técnico, los de 6.4: en River, 3 de jugadores y 9 de profes.
    torneo.reglas = torneo.reglas | {"choque_de_profes": "todo_el_cuerpo_tecnico"}
    torneo.save()
    pares = pares_de_equipos(torneo)
    assert Counter(p.motivo for p in pares) == {"jugador": 7, "profe": 29}
    assert sum(p.a in river and p.b in river for p in pares) == 3 + 9
    # Por defecto (P57), solo el entrenador: quedan menos pares de profes.
    torneo.reglas = torneo.reglas | {"choque_de_profes": "entrenador"}
    torneo.save()
    pares = pares_de_equipos(torneo)
    assert Counter(p.motivo for p in pares) == {"jugador": 7, "profe": 12}


@pytest.mark.django_db
def test_un_profe_en_tres_equipos_da_tres_pares_y_sin_datos_personales() -> None:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    club = Club.objects.create(nombre="Club")
    equipos = [
        Equipo.objects.create(club=club, categoria=c, nombre="Club")
        for c in torneo.categorias.filter(
            categoria__in=["Sub 7", "Sub 8", "Sub 9"], nivel="inicial"
        )
    ]
    profe = Persona.objects.create(nombres="P", apellidos="Inventado", clave_documento="7000001")
    jugador = Persona.objects.create(
        nombres="J", apellidos="Inventado", nacimiento=date(2018, 1, 1)
    )
    for equipo in equipos:
        Profe.objects.create(persona=profe, equipo=equipo, rol="entrenador")
    Jugador.objects.create(persona=jugador, equipo=equipos[0])
    Profe.objects.create(persona=jugador, equipo=equipos[1], rol="asistente")  # jugador y profe

    # P57: por defecto el choque cuenta solo para el entrenador. El que juega en uno y es
    # asistente en otro no tiene que estar en la cancha del segundo.
    pares = pares_de_equipos(torneo)
    assert len(pares) == 3
    assert Counter(p.motivo for p in pares) == {"profe": 3}
    assert {f.name for f in fields(pares[0])} == {"a", "b", "motivo"}
    assert all(isinstance(p.a, int) and isinstance(p.b, int) for p in pares)

    torneo.reglas = torneo.reglas | {"choque_de_profes": "todo_el_cuerpo_tecnico"}
    torneo.save()
    assert len(pares_de_equipos(torneo)) == 4


@pytest.mark.django_db
def test_p57_un_asistente_o_delegado_compartido_no_choca_por_defecto() -> None:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    club = Club.objects.create(nombre="Club")
    sub7, sub8 = (
        Equipo.objects.create(club=club, categoria=c, nombre="Club")
        for c in torneo.categorias.filter(categoria__in=["Sub 7", "Sub 8"], nivel="inicial")
    )
    persona = Persona.objects.create(nombres="D", apellidos="Inventado", clave_documento="7000002")
    Profe.objects.create(persona=persona, equipo=sub7, rol="delegado")
    Profe.objects.create(persona=persona, equipo=sub8, rol="entrenador")
    assert pares_de_equipos(torneo) == []
    torneo.reglas = torneo.reglas | {"choque_de_profes": "todo_el_cuerpo_tecnico"}
    torneo.save()
    assert [p.motivo for p in pares_de_equipos(torneo)] == ["profe"]
