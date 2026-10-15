"""T13.8 (P79): para que F11 entre en la cancha 3 no se usan jueves (quedan para las
suspensiones). Se amplía el horario de C3 los sábados y domingos. Datos inventados."""

from datetime import date

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.capacidad import GrupoDeCanchas
from dominio.config import cargar_config
from torneo.models import Franja, Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.views.programar import sugerencia_para_que_entre


@pytest.fixture
def torneo() -> Torneo:
    return cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


@pytest.mark.django_db
def test_agregar_tiempo_en_todos_los_fines_de_semana(org: Client, torneo: Torneo) -> None:
    c3 = torneo.canchas.get(codigo="C3")
    respuesta = org.post(
        "/calendario/agregar-dia/",
        {
            "dia": "2026-10-24",
            "desde": "06:30",
            "hasta": "07:30",
            "canchas": [c3.pk],
            "fines_de_semana": "on",
        },
    )
    assert respuesta.status_code == 302
    extras = Franja.objects.filter(torneo=torneo, tipo=Franja.Tipo.ENTRE_SEMANA)
    dias = sorted(timezone.localtime(f.inicio).date() for f in extras)
    # Los ocho sábados y domingos del torneo, del 24/10 al 15/11.
    assert dias == [
        date(2026, 10, 24), date(2026, 10, 25), date(2026, 10, 31), date(2026, 11, 1),
        date(2026, 11, 7), date(2026, 11, 8), date(2026, 11, 14), date(2026, 11, 15),
    ]  # fmt: skip
    assert all(list(f.canchas.all()) == [c3] for f in extras)
    assert all(timezone.localtime(f.inicio).hour == 6 for f in extras)


def test_la_sugerencia_es_el_fin_de_semana_y_no_el_jueves() -> None:
    grupo = GrupoDeCanchas(
        ("C3",), ("Sub 10 Avanzado",), pedido=6000, disponible=5000, ubicable=5000
    )
    texto = sugerencia_para_que_entre(grupo, dias_de_fin_de_semana=8)
    assert "sábados y domingos" in texto and "C3" in texto
    assert "jueves" not in texto.lower()
    # Faltan 1.000 minutos en 8 días: unos 125 por día, redondeado a la media hora.
    assert "2,5 h por día" in texto


def test_sin_fines_de_semana_no_sugiere_nada() -> None:
    grupo = GrupoDeCanchas(("C3",), (), pedido=6000, disponible=5000, ubicable=5000)
    assert sugerencia_para_que_entre(grupo, dias_de_fin_de_semana=0) == ""
