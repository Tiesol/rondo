"""T13.27: Reglas y el asistente sin las etiquetas P (son para nosotros), sin la regla "Jugador
en dos equipos" (P7: se queda su valor por defecto) y con textos que se entienden."""

import re

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import Reglas, cargar_config, describir_reglas
from torneo.models import Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


def test_p7_no_se_muestra_y_queda_su_valor_por_defecto() -> None:
    assert "jugador_en_dos_equipos" not in {d.nombre for d in describir_reglas()}
    assert Reglas().jugador_en_dos_equipos == "mismo_club_otra_categoria"


def test_textos_nuevos() -> None:
    ayuda = {d.nombre: d.ayuda for d in describir_reglas()}
    assert "tardíos" in ayuda["cierre_inscripcion"]
    assert "semis y finales" in ayuda["eliminacion_desde_fin_de_semana"]
    assert "sugiere primero" in ayuda["dia_para_reprogramar"]
    assert ayuda["criterio_de_desempate"].startswith("Reglamento 2025: puntos entre los empatados")


@pytest.mark.django_db
def test_reglas_inicio_y_asistente_sin_etiquetas_p(org: Client) -> None:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    for url in (f"/torneos/{torneo.pk}/reglas/", "/", "/torneos/nuevo/4/"):
        html = org.get(url).content.decode()
        assert not re.search(r">P\d+<", html), url
        assert "pregunta al organizador" not in html, url
        assert "Jugador en dos equipos" not in html, url
