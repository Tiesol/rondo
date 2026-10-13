"""Configuración común de los tests."""

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def cache_limpia() -> Iterator[None]:
    """Cada test arranca sin intentos de login contados (T6.3) ni otros restos en la caché."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def agregar_jueves() -> Callable[[Any], None]:
    """Agrega los tres jueves de 16 a 20 que hacen falta con Sub 10 y Sub 11 Avanzado en F11.

    Con F11 (P60), la cancha 3 pide 5.610 minutos y da 4.560: sin días extra no entra todo
    (PROGRESO, H8). La convocatoria propone el jueves para reprogramar.
    """
    from datetime import datetime

    from django.utils import timezone

    from torneo.models import Franja

    def agregar(torneo: Any) -> None:
        for mes, dia in ((10, 29), (11, 5), (11, 12)):
            Franja.objects.create(
                torneo=torneo,
                tipo=Franja.Tipo.ENTRE_SEMANA,
                inicio=timezone.make_aware(datetime(2026, mes, dia, 16)),
                fin=timezone.make_aware(datetime(2026, mes, dia, 20)),
            )

    return agregar
