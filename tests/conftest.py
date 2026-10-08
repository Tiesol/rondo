"""Configuración común de los tests."""

from collections.abc import Iterator

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def cache_limpia() -> Iterator[None]:
    """Cada test arranca sin intentos de login contados (T6.3) ni otros restos en la caché."""
    cache.clear()
    yield
    cache.clear()
