"""Hallazgos de la revisión de cierre de la fase 2 (ver PROGRESO.md). Datos inventados."""

import io
from datetime import date

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Persona
from torneo.servicios.configuracion import cargar_configuracion


@pytest.mark.django_db
def test_la_demo_se_niega_si_hay_personas_que_no_son_de_la_demo() -> None:
    """Una persona sin equipo puede ser un dato real a medio cargar."""
    Persona.objects.create(nombres="Nombre", apellidos="Suelto", nacimiento=date(2017, 1, 1))
    with pytest.raises(CommandError, match="no son de demo"):
        call_command("generar_demo", "--soy-la-demo", stdout=io.StringIO())
    assert not Equipo.objects.exists()


@pytest.mark.django_db
def test_sin_rol_no_se_ven_los_planteles(client: Client) -> None:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    equipo = Equipo.objects.create(
        club=Club.objects.create(nombre="River Plate"),
        categoria=torneo.categorias.get(categoria="Sub 9", nivel="avanzado"),
        nombre="River Plate",
    )
    client.force_login(User.objects.create_user("nadie", password="x"))
    for seccion in ("plantel", "cuerpo-tecnico"):
        respuesta = client.get(f"/equipos/{equipo.pk}/{seccion}/")
        assert respuesta.status_code == 403
        assert "Solo la organización puede ver los planteles" in respuesta.content.decode()
