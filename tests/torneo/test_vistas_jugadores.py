"""T2.6: alta de jugadores y profes con avisos en vivo, y verificación (INS-12).

Cubre los criterios de inscripción de la sección 10 del contexto desde la pantalla.
Datos inventados.
"""

from datetime import date
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Jugador, Persona, Profe, Torneo
from torneo.permisos import MESA
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.inscripcion import DatosPersona, agregar_jugador, agregar_profe

HOY = date(2026, 10, 10)


@pytest.fixture
def torneo() -> Torneo:
    return cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))


def nuevo_equipo(torneo: Torneo, club: str, categoria: str, nivel: str) -> Equipo:
    club_obj, _ = Club.objects.get_or_create(nombre=club)
    cn: CategoriaNivel = torneo.categorias.get(categoria=categoria, nivel=nivel)
    return Equipo.objects.create(club=club_obj, categoria=cn, nombre=club)


@pytest.fixture
def river9(torneo: Torneo) -> Equipo:
    return nuevo_equipo(torneo, "River Plate", "Sub 9", "avanzado")


@pytest.fixture
def mesa(client: Client) -> Client:
    usuario = User.objects.create_user("mesa", password="x")
    usuario.groups.add(Group.objects.get(name=MESA))
    client.force_login(usuario)
    return client


def jugador(**cambios: Any) -> dict[str, Any]:
    datos = {
        "documento": "1234567 SC",
        "nombres": "Nombre",
        "apellidos": "Inventado",
        "nacimiento": "2017-03-14",
        "dorsal": "10",
    }
    return datos | cambios


def url(equipo: Equipo, que: str = "jugadores/nuevo") -> str:
    return f"/equipos/{equipo.pk}/{que}/"


# ---------- Sección 10: inscripción ----------


@pytest.mark.django_db
def test_rechaza_a_un_jugador_mas_grande_que_su_categoria(mesa: Client, river9: Equipo) -> None:
    respuesta = mesa.post(url(river9), jugador(nacimiento="2015-05-05"))
    assert respuesta.status_code == 200
    assert "es mayor para Sub 9" in respuesta.content.decode()
    assert not Jugador.objects.exists()


@pytest.mark.django_db
def test_acepta_a_uno_mas_chico(mesa: Client, river9: Equipo) -> None:
    respuesta = mesa.post(url(river9), jugador(nacimiento="2018-05-05"))
    assert respuesta["Location"] == url(river9, "plantel")
    assert Jugador.objects.get().equipo == river9


@pytest.mark.django_db
def test_no_deja_pasar_del_maximo(mesa: Client, river9: Equipo) -> None:
    for i in range(14):
        agregar_jugador(
            river9,
            DatosPersona(f"{3000000 + i}", "N", f"I{i}", date(2017, 1, 1)),
            i + 1,
            hoy=HOY,
            es_organizacion=True,
        )
    respuesta = mesa.post(url(river9), jugador(dorsal="50"))
    assert respuesta.status_code == 200
    assert "el máximo" in respuesta.content.decode()
    assert river9.jugadores.count() == 14


@pytest.mark.django_db
def test_avisa_cuando_falta_llegar_al_minimo(mesa: Client, river9: Equipo) -> None:
    en_vivo = mesa.post(url(river9, "jugadores/revisar"), jugador()).content.decode()
    assert "Faltan 11 para el mínimo" in en_vivo
    ficha = mesa.post(url(river9), jugador(), follow=True).content.decode()
    assert "1 de 14 jugadores" in ficha  # en la ficha, como chip y no como aviso flotante
    assert "Faltan 11 para el mínimo" not in ficha


@pytest.mark.django_db
def test_avisa_cuando_un_ci_ya_esta_en_otro_equipo(
    mesa: Client, torneo: Torneo, river9: Equipo
) -> None:
    river11 = nuevo_equipo(torneo, "River Plate", "Sub 11", "avanzado")
    agregar_jugador(
        river11,
        DatosPersona("1234567", "Nombre", "Inventado", date(2017, 3, 14)),
        7,
        hoy=HOY,
        es_organizacion=True,
    )
    vivo = mesa.post(url(river9, "jugadores/revisar"), {"documento": "1.234.567 sc"})
    assert "Ya juega en Sub 11 Avanzado de River Plate" in vivo.content.decode()
    guardado = mesa.post(url(river9), jugador(), follow=True)
    assert "Ya juega en Sub 11 Avanzado de River Plate" in guardado.content.decode()
    assert Jugador.objects.count() == 2  # el aviso no bloquea


@pytest.mark.django_db
def test_limita_el_cuerpo_tecnico_a_tres_con_rol(mesa: Client, river9: Equipo) -> None:
    for i, rol in enumerate(["entrenador", "asistente", "delegado"]):
        agregar_profe(
            river9,
            DatosPersona(f"{4000000 + i}", "P", f"I{i}", None),
            rol,
            hoy=HOY,
            es_organizacion=True,
        )
    respuesta = mesa.post(
        url(river9, "profes/nuevo"),
        {"documento": "4999999", "nombres": "Otro", "apellidos": "Más", "rol": "asistente"},
    )
    assert respuesta.status_code == 200
    assert "ya tiene 3 personas" in respuesta.content.decode()
    assert Profe.objects.count() == 3


@pytest.mark.django_db
def test_el_rol_sale_de_la_configuracion(mesa: Client, river9: Equipo) -> None:
    html = mesa.get(url(river9, "profes/nuevo")).content.decode()
    for rol in ("entrenador", "asistente", "delegado"):
        assert f'value="{rol}"' in html


# ---------- Avisos en vivo ----------


@pytest.mark.django_db
def test_en_vivo_no_guarda_y_devuelve_solo_los_avisos(mesa: Client, river9: Equipo) -> None:
    respuesta = mesa.post(url(river9, "jugadores/revisar"), jugador(nacimiento="2015-01-01"))
    html = respuesta.content.decode()
    assert "<html" not in html
    assert 'id="hallazgos"' in html
    assert "es mayor" in html
    assert not Persona.objects.exists()


@pytest.mark.django_db
def test_en_vivo_no_reclama_lo_que_todavia_no_se_escribio(mesa: Client, river9: Equipo) -> None:
    html = mesa.post(url(river9, "jugadores/revisar"), {"documento": "1234567"}).content.decode()
    assert "Falta la fecha de nacimiento" not in html


@pytest.mark.django_db
def test_un_documento_mal_escrito_se_avisa_en_vivo(mesa: Client, river9: Equipo) -> None:
    html = mesa.post(url(river9, "jugadores/revisar"), {"documento": "12#45"}).content.decode()
    assert "Ejemplos válidos" in html


# ---------- Datos personales fuera de los logs ----------


@pytest.mark.django_db
@pytest.mark.parametrize("que", ["jugadores/nuevo", "jugadores/revisar", "profes/nuevo"])
def test_los_formularios_con_datos_personales_son_sensibles(
    mesa: Client, river9: Equipo, que: str
) -> None:
    respuesta = mesa.post(url(river9, que), jugador())
    assert respuesta.wsgi_request.sensitive_post_parameters == "__ALL__"  # type: ignore[attr-defined]


# ---------- INS-12: verificación ----------


@pytest.mark.django_db
def test_ins_12_la_mesa_marca_al_jugador_como_verificado(mesa: Client, river9: Equipo) -> None:
    resultado = agregar_jugador(
        river9,
        DatosPersona("1234567", "N", "I", date(2017, 1, 1)),
        1,
        hoy=HOY,
        es_organizacion=True,
    )
    assert resultado.registro is not None
    pk = resultado.registro.pk
    respuesta = mesa.post(f"/jugadores/{pk}/verificar/", headers={"HX-Request": "true"})
    assert respuesta.status_code == 200
    assert "Verificado" in respuesta.content.decode()
    assert Jugador.objects.get(pk=pk).verificado
    mesa.post(f"/jugadores/{pk}/verificar/")
    assert not Jugador.objects.get(pk=pk).verificado


@pytest.mark.django_db
def test_ins_12_sin_rol_no_se_verifica(client: Client, river9: Equipo) -> None:
    resultado = agregar_jugador(
        river9,
        DatosPersona("1234567", "N", "I", date(2017, 1, 1)),
        1,
        hoy=HOY,
        es_organizacion=True,
    )
    assert resultado.registro is not None
    client.force_login(User.objects.create_user("nadie", password="x"))
    assert client.post(f"/jugadores/{resultado.registro.pk}/verificar/").status_code == 403
    assert not Jugador.objects.get().verificado
