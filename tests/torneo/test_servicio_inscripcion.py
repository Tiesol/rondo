"""T2.4: servicio de inscripción. Datos inventados."""

from datetime import date

import pytest
from django.conf import settings

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Jugador, Persona, Profe, Torneo
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.inscripcion import (
    DatosPersona,
    agregar_jugador,
    agregar_profe,
    revisar_jugador,
)

HOY = date(2026, 10, 10)


@pytest.fixture
def torneo() -> Torneo:
    return cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))


def equipo(torneo: Torneo, club: str, categoria: str, nivel: str) -> Equipo:
    club_obj, _ = Club.objects.get_or_create(nombre=club)
    return Equipo.objects.create(
        club=club_obj,
        categoria=torneo.categorias.get(categoria=categoria, nivel=nivel),
        nombre=club,
    )


def nino(documento: str = "1234567 SC", nacimiento: date = date(2017, 3, 14)) -> DatosPersona:
    return DatosPersona(documento, "Nombre", "Inventado", nacimiento)


def reglas(resultado: object) -> list[tuple[str, str]]:
    return [(h.nivel, h.regla) for h in resultado.hallazgos]  # type: ignore[attr-defined]


@pytest.mark.django_db
def test_agrega_un_jugador_y_crea_a_la_persona(torneo: Torneo) -> None:
    river9 = equipo(torneo, "River Plate", "Sub 9", "avanzado")
    resultado = agregar_jugador(river9, nino(), dorsal=10, hoy=HOY, es_organizacion=True)
    assert resultado.guardado
    jugador = Jugador.objects.get()
    assert (jugador.equipo, jugador.dorsal) == (river9, 10)
    assert jugador.persona.clave_documento == "1234567"
    assert jugador.persona.documento == "1234567 SC"


@pytest.mark.django_db
def test_mismo_club_otra_categoria_guarda_con_aviso(torneo: Torneo) -> None:
    river11 = equipo(torneo, "River Plate", "Sub 11", "avanzado")
    river9 = equipo(torneo, "River Plate", "Sub 9", "avanzado")
    agregar_jugador(river9, nino(), dorsal=7, hoy=HOY, es_organizacion=True)
    resultado = agregar_jugador(river11, nino("1234567"), dorsal=7, hoy=HOY, es_organizacion=True)
    assert resultado.guardado
    assert ("aviso", "INS-05") in reglas(resultado)
    assert Persona.objects.count() == 1
    assert Jugador.objects.count() == 2


@pytest.mark.django_db
def test_con_un_error_no_se_guarda_nada(torneo: Torneo) -> None:
    river9 = equipo(torneo, "River Plate", "Sub 9", "avanzado")
    resultado = agregar_jugador(
        river9, nino(nacimiento=date(2014, 1, 1)), dorsal=10, hoy=HOY, es_organizacion=True
    )
    assert not resultado.guardado
    assert ("error", "INS-02") in reglas(resultado)
    assert Persona.objects.count() == 0
    assert Jugador.objects.count() == 0


@pytest.mark.django_db
def test_el_maximo_no_se_pasa(torneo: Torneo) -> None:
    river9 = equipo(torneo, "River Plate", "Sub 9", "avanzado")
    for i in range(14):
        assert agregar_jugador(
            river9, nino(f"{1000000 + i}"), dorsal=i + 1, hoy=HOY, es_organizacion=True
        ).guardado
    resultado = agregar_jugador(river9, nino("2000000"), dorsal=50, hoy=HOY, es_organizacion=True)
    assert not resultado.guardado
    assert ("error", "INS-03") in reglas(resultado)
    assert river9.jugadores.count() == 14


@pytest.mark.django_db
def test_un_documento_que_no_se_reconoce_es_error(torneo: Torneo) -> None:
    river9 = equipo(torneo, "River Plate", "Sub 9", "avanzado")
    resultado = agregar_jugador(river9, nino("12#45"), dorsal=1, hoy=HOY, es_organizacion=True)
    assert not resultado.guardado
    assert ("error", "INS-04") in reglas(resultado)


@pytest.mark.django_db
def test_sin_documento_se_guarda_con_aviso_y_cada_uno_es_otra_persona(torneo: Torneo) -> None:
    river9 = equipo(torneo, "River Plate", "Sub 9", "avanzado")
    uno = agregar_jugador(river9, nino(""), dorsal=1, hoy=HOY, es_organizacion=True)
    otro = agregar_jugador(river9, nino("S/N"), dorsal=2, hoy=HOY, es_organizacion=True)
    assert uno.guardado and otro.guardado
    assert ("aviso", "INS-10") in reglas(uno)
    assert Persona.objects.filter(clave_documento="").count() == 2


@pytest.mark.django_db
def test_si_el_documento_ya_existe_valen_los_datos_guardados(torneo: Torneo) -> None:
    river11 = equipo(torneo, "River Plate", "Sub 11", "avanzado")
    river9 = equipo(torneo, "River Plate", "Sub 9", "avanzado")
    agregar_jugador(river9, nino(), dorsal=7, hoy=HOY, es_organizacion=True)
    distinto = DatosPersona("1234567", "Otro", "Nombre", date(2015, 2, 2))
    resultado = agregar_jugador(river11, distinto, dorsal=7, hoy=HOY, es_organizacion=True)
    assert resultado.guardado
    assert ("aviso", "INS-04") in reglas(resultado)
    assert Persona.objects.get().nombres == "Nombre"


@pytest.mark.django_db
def test_revisar_no_guarda(torneo: Torneo) -> None:
    river9 = equipo(torneo, "River Plate", "Sub 9", "avanzado")
    hallazgos = revisar_jugador(river9, nino(), dorsal=None, hoy=HOY, es_organizacion=True)
    assert [(h.nivel, h.regla) for h in hallazgos] == [("aviso", "INS-03"), ("aviso", "INS-09")]
    assert Persona.objects.count() == 0


@pytest.mark.django_db
def test_un_profe_en_dos_equipos_de_distinto_club(torneo: Torneo) -> None:
    river9 = equipo(torneo, "River Plate", "Sub 9", "avanzado")
    leones = equipo(torneo, "Leones", "Sub 11", "inicial")
    profe = DatosPersona("7654321 LP", "Profe", "Inventado", None)
    assert agregar_profe(river9, profe, "entrenador", hoy=HOY, es_organizacion=True).guardado
    resultado = agregar_profe(leones, profe, "entrenador", hoy=HOY, es_organizacion=True)
    assert resultado.guardado
    assert ("aviso", "INS-06") in reglas(resultado)
    assert Profe.objects.count() == 2
    assert Persona.objects.count() == 1


@pytest.mark.django_db
def test_un_segundo_entrenador_no_se_guarda(torneo: Torneo) -> None:
    river9 = equipo(torneo, "River Plate", "Sub 9", "avanzado")
    uno = DatosPersona("7654321", "Profe", "Uno", None)
    dos = DatosPersona("7654322", "Profe", "Dos", None)
    agregar_profe(river9, uno, "entrenador", hoy=HOY, es_organizacion=True)
    resultado = agregar_profe(river9, dos, "entrenador", hoy=HOY, es_organizacion=True)
    assert not resultado.guardado
    assert ("error", "INS-08") in reglas(resultado)


@pytest.mark.django_db
def test_despues_del_cierre_la_mesa_no_agrega(torneo: Torneo) -> None:
    torneo.reglas = torneo.reglas | {"cierre_inscripcion": "2026-10-05"}
    torneo.save()
    river9 = equipo(torneo, "River Plate", "Sub 9", "avanzado")
    mesa = agregar_jugador(river9, nino(), dorsal=1, hoy=HOY, es_organizacion=False)
    assert not mesa.guardado
    assert ("error", "INS-11") in reglas(mesa)
    assert agregar_jugador(river9, nino(), dorsal=1, hoy=HOY, es_organizacion=True).guardado
