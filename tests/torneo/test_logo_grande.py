"""T13.25: la marca de la JMP tiene que verse. El logo mide al menos 44 px en la barra y el menú
lateral, y al menos 72 px en el login y la cabecera pública (antes 34 y 52)."""

import re

from django.conf import settings


def _ancho(regla: str) -> int:
    css = (settings.BASE_DIR / "frontend" / "tailwind.css").read_text()
    bloque = re.search(re.escape(regla) + r"\s*\{([^}]*)\}", css)
    assert bloque is not None, regla
    ancho = re.search(r"width:\s*(\d+)px", bloque.group(1))
    assert ancho is not None
    return int(ancho.group(1))


def test_el_logo_se_ve() -> None:
    assert _ancho(".marca") >= 44
    assert _ancho(".marca.grande") >= 72
