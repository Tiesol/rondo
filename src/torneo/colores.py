"""Contraste de colores (WCAG 2), para los colores que elige el organizador (TU.7)."""

AZUL_MARINO = "#0d2440"
BLANCO = "#ffffff"


def _luminancia(color: str) -> float:
    canales = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lineales = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]
    rojo, verde, azul = lineales
    return 0.2126 * rojo + 0.7152 * verde + 0.0722 * azul


def contraste(uno: str, otro: str) -> float:
    """Entre 1 (igual) y 21 (negro sobre blanco). El texto normal pide 4,5 o más."""
    claro, oscuro = sorted((_luminancia(uno), _luminancia(otro)), reverse=True)
    return (claro + 0.05) / (oscuro + 0.05)


def texto_sobre(fondo: str) -> str:
    """Azul marino o blanco, el que más se lea sobre ese fondo."""
    return max((AZUL_MARINO, BLANCO), key=lambda texto: contraste(fondo, texto))
