"""T5.8: el ensayo de la demo, de punta a punta, con datos inventados.

demo → fixtures → programar → bloqueo de la ACF → propuestas → aplicar → PNG del día.
"""

import io
from datetime import timedelta
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from torneo.models import Bloqueo, Corrida, Partido, Persona, Torneo
from torneo.servicios.fixture import generar_fixtures_faltantes
from torneo.servicios.programador import verificar_torneo


@pytest.mark.lento
@pytest.mark.django_db
def test_la_demo_de_punta_a_punta(client: Client, settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 90
    call_command("generar_demo", "--soy-la-demo", stdout=io.StringIO())
    torneo = Torneo.objects.get(es_demo=True)
    client.force_login(User.objects.create_superuser("sebastian", password="x"))

    assert client.post(f"/torneos/{torneo.pk}/fixtures/").status_code == 302
    assert not generar_fixtures_faltantes(torneo).generadas  # ya estaban todos

    client.post(f"/torneos/{torneo.pk}/programar/")
    corrida = Corrida.objects.get(tipo=Corrida.Tipo.PROGRAMAR)
    assert corrida.resultado["choques"] == {}
    assert corrida.resultado["sin_ubicar"] == []

    victima = (
        Partido.objects.filter(categoria__torneo=torneo, fase="grupos", inicio__isnull=False)
        .order_by("inicio")
        .first()
    )
    assert victima is not None and victima.inicio is not None and victima.local is not None
    local = timezone.localtime(victima.inicio)
    client.post(
        f"/torneos/{torneo.pk}/acf/",
        {
            "equipos": [victima.local.pk],
            "dia": local.date().isoformat(),
            "desde": (local - timedelta(minutes=30)).strftime("%H:%M"),
            "hasta": (local + timedelta(minutes=90)).strftime("%H:%M"),
            "motivo": "Partido de la ACF",
        },
    )
    bloqueo = Bloqueo.objects.get()
    respuesta = client.post(f"/bloqueos/{bloqueo.pk}/propuestas/")
    reprogramar = Corrida.objects.get(tipo=Corrida.Tipo.REPROGRAMAR)
    assert 2 <= len(reprogramar.resultado["propuestas"]) <= 3
    assert "Recomendada" in client.get(respuesta["Location"]).content.decode()

    client.post(f"/corridas/{reprogramar.pk}/aplicar/0/")
    assert verificar_torneo(torneo) == {}

    png = client.get(f"/calendario/{local.date().isoformat()}/png/").content.decode()
    assert "FIXTURE" in png
    for persona in Persona.objects.all()[:200]:
        assert f"{persona.nombres} {persona.apellidos}" not in png
        if persona.documento:
            assert persona.documento not in png
