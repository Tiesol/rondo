"""Hallazgos de la revisión de cierre de la fase 5 (ver PROGRESO.md)."""

from typing import Any

import pytest

from dominio.config import cargar_config
from torneo.models import Bloqueo
from torneo.servicios import reprogramar
from torneo.servicios.configuracion import cargar_configuracion


@pytest.mark.django_db
def test_las_propuestas_reparten_el_limite_de_tiempo(monkeypatch: Any, settings: Any) -> None:
    """Tres resoluciones con el límite entero podían tardar el triple (gunicorn corta a 300 s)."""
    settings.PROGRAMADOR_SEGUNDOS = 60
    pedido: dict[str, Any] = {}

    def proponer_falso(*args: Any, **kwargs: Any) -> list[Any]:
        pedido.update(kwargs)
        return []

    monkeypatch.setattr(reprogramar, "proponer", proponer_falso)
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    franja = torneo.franjas.first()
    assert franja is not None
    bloqueo = Bloqueo.objects.create(torneo=torneo, inicio=franja.inicio, fin=franja.fin)
    reprogramar.calcular_propuestas(bloqueo)
    assert pedido["segundos"] * pedido["cuantas"] <= 60
