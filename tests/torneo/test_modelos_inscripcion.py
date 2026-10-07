"""T2.3: modelos de inscripción, restricciones en la base y logs sin datos personales.

Todos los datos son inventados.
"""

import io
import logging
import sys
from datetime import date

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, Jugador, Persona, Profe
from torneo.servicios.configuracion import cargar_configuracion

CI_INVENTADO = "9988776"


@pytest.fixture
def sub9() -> CategoriaNivel:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    return torneo.categorias.get(categoria="Sub 9", nivel="avanzado")


@pytest.fixture
def equipo(sub9: CategoriaNivel) -> Equipo:
    club = Club.objects.create(nombre="River Plate")
    return Equipo.objects.create(club=club, categoria=sub9, nombre="River Plate")


def persona(clave: str = CI_INVENTADO, **datos: object) -> Persona:
    return Persona.objects.create(
        tipo_documento="ci" if clave else "",
        documento=clave,
        clave_documento=clave,
        nombres="Nombre",
        apellidos="Inventado",
        nacimiento=date(2017, 1, 1),
        **datos,
    )


@pytest.mark.django_db
def test_el_ci_es_unico_cuando_existe() -> None:
    persona()
    with pytest.raises(IntegrityError), transaction.atomic():
        persona()


@pytest.mark.django_db
def test_varias_personas_pueden_tener_el_documento_pendiente() -> None:
    persona("")
    persona("")
    assert Persona.objects.filter(clave_documento="").count() == 2


@pytest.mark.django_db
def test_el_dorsal_es_unico_en_el_equipo_si_existe(equipo: Equipo) -> None:
    Jugador.objects.create(persona=persona("1111111"), equipo=equipo, dorsal=10)
    Jugador.objects.create(persona=persona("2222222"), equipo=equipo, dorsal=None)
    Jugador.objects.create(persona=persona("3333333"), equipo=equipo, dorsal=None)
    with pytest.raises(IntegrityError), transaction.atomic():
        Jugador.objects.create(persona=persona("4444444"), equipo=equipo, dorsal=10)


@pytest.mark.django_db
def test_una_persona_una_sola_vez_por_equipo(equipo: Equipo) -> None:
    alguien = persona()
    Jugador.objects.create(persona=alguien, equipo=equipo)
    with pytest.raises(IntegrityError), transaction.atomic():
        Jugador.objects.create(persona=alguien, equipo=equipo)
    Profe.objects.create(persona=alguien, equipo=equipo, rol="entrenador")
    with pytest.raises(IntegrityError), transaction.atomic():
        Profe.objects.create(persona=alguien, equipo=equipo, rol="asistente")


@pytest.mark.django_db
def test_un_equipo_por_club_categoria_y_nombre(equipo: Equipo) -> None:
    Equipo.objects.create(club=equipo.club, categoria=equipo.categoria, nombre="River Plate 2")
    with pytest.raises(IntegrityError), transaction.atomic():
        Equipo.objects.create(club=equipo.club, categoria=equipo.categoria, nombre="River Plate")


@pytest.mark.django_db
def test_no_se_borra_una_categoria_con_equipos(equipo: Equipo) -> None:
    from django.db.models import ProtectedError

    with pytest.raises(ProtectedError):
        equipo.categoria.delete()


@pytest.mark.django_db
def test_el_log_no_muestra_el_ci_de_un_error_de_la_base() -> None:
    """Pendiente de la revisión de la fase 0: el texto de Postgres trae el valor repetido."""
    persona()
    try:
        with transaction.atomic():
            persona()
    except IntegrityError:
        error = sys.exc_info()
    assert CI_INVENTADO in str(error[1]), "el error de Postgres sí trae el CI"

    consola = next(h for h in logging.getLogger().handlers if h.get_name() == "consola")
    salida = io.StringIO()
    anterior = consola.setStream(salida)  # type: ignore[attr-defined]
    try:
        logging.getLogger("django.request").error("Internal Server Error: /x/", exc_info=error)
    finally:
        consola.setStream(anterior)  # type: ignore[attr-defined]
    texto = salida.getvalue()
    assert "Internal Server Error" in texto
    assert "IntegrityError" in texto
    assert CI_INVENTADO not in texto


@pytest.mark.django_db
def test_el_log_de_otros_errores_queda_entero() -> None:
    consola = next(h for h in logging.getLogger().handlers if h.get_name() == "consola")
    salida = io.StringIO()
    anterior = consola.setStream(salida)  # type: ignore[attr-defined]
    try:
        try:
            raise ValueError("detalle útil")
        except ValueError:
            logging.getLogger("django.request").error("Falla", exc_info=True)
    finally:
        consola.setStream(anterior)  # type: ignore[attr-defined]
    assert "detalle útil" in salida.getvalue()


@pytest.mark.django_db
def test_cargar_clubes_es_idempotente_y_trae_alias() -> None:
    call_command("cargar_clubes", stdout=io.StringIO())
    call_command("cargar_clubes", stdout=io.StringIO())
    jmp = Club.objects.get(nombre="JMP")
    assert "JMP Academy" in jmp.alias
    assert Club.objects.filter(nombre="River Plate").count() == 1
    assert Club.buscar("jmp soccer") == jmp
    assert Club.buscar("Petrolero") == Club.objects.get(nombre="Oriente Petrolero")
    assert Club.buscar("No existe") is None


@pytest.mark.django_db
def test_el_admin_de_club_carga_alias_uno_por_linea(client: Client) -> None:
    client.force_login(User.objects.create_superuser("sebastian", password="x"))
    respuesta = client.post(
        "/admin/torneo/club/add/",
        {"nombre": "Club Inventado", "alias_texto": "Inventado FC\n  Los Inventados  \n"},
    )
    assert respuesta.status_code == 302
    assert Club.objects.get(nombre="Club Inventado").alias == ["Inventado FC", "Los Inventados"]
