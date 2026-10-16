"""T13.37: "¿Entra todo?" más corto. La capacidad en una línea y las categorías como chips,
plegadas ("Ver categorías (10)")."""

import io
import re

import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import Client

from dominio.capacidad import GrupoDeCanchas
from torneo.models import Torneo
from torneo.permisos import ORGANIZACION
from torneo.servicios.fixture import generar_fixtures_faltantes
from torneo.views.programar import una_linea


def test_una_linea_si_entra() -> None:
    grupo = GrupoDeCanchas(
        ("C1", "C2"), ("Sub 9",), pedido=93 * 60, disponible=168 * 60, ubicable=93 * 60
    )
    assert una_linea(grupo, partidos=130, turno=50) == "130 partidos · entran unos 90 más de 50 min"


def test_una_linea_si_no_entra() -> None:
    grupo = GrupoDeCanchas(
        ("C3",), ("Sub 10",), pedido=94 * 60, disponible=88 * 60, ubicable=88 * 60
    )
    assert una_linea(grupo, partidos=93, turno=75) == "Faltan 6 h · 93 partidos"


@pytest.mark.django_db
def test_las_categorias_van_como_chips_plegados(client: Client) -> None:
    call_command("generar_demo", "--soy-la-demo", stdout=io.StringIO())
    torneo = Torneo.objects.get(es_demo=True)
    generar_fixtures_faltantes(torneo)
    usuario = User.objects.create_user("orga", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)

    html = client.get(f"/torneos/{torneo.pk}/programar/").content.decode()

    plegadas = re.findall(
        r'<details class="desplegable categorias">\s*<summary>Ver categorías \((\d+)\)</summary>'
        r"(.*?)</details>",
        html,
        re.S,
    )
    assert len(plegadas) == 2  # C1 y C2, y C3
    for cantidad, chips in plegadas:
        assert chips.count('class="chip neutro') == int(cantidad)
    assert "Sub 5, Sub 6" not in html  # ya no van en un renglón con comas
    assert re.search(r"\d+ partidos · entran unos \d+ más de \d+ min", html)  # C1 y C2
    assert re.search(r"Faltan [\d,]+ h · \d+ partidos", html)  # C3, sin tiempo agregado
    # La frase completa queda para los lectores de pantalla, en la barra.
    assert re.search(r'class="barra-cap" role="img" aria-label="C1 y C2: \d+ partidos', html)
