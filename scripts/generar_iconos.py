"""Genera los íconos de la app (PWA) sin dependencias: fondo azul marino y un anillo dorado.

Son genéricos a propósito: el logo del organizador llega con las imágenes (R47).
Uso: uv run python scripts/generar_iconos.py
"""

import struct
import zlib
from pathlib import Path

AZUL = (13, 36, 64)
ORO = (242, 207, 58)
DESTINO = Path(__file__).resolve().parents[1] / "src" / "torneo" / "static" / "iconos"


def _png(ancho: int, filas: list[bytes]) -> bytes:
    def bloque(tipo: bytes, datos: bytes) -> bytes:
        return (
            struct.pack(">I", len(datos))
            + tipo
            + datos
            + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)
        )

    crudo = b"".join(b"\x00" + fila for fila in filas)
    return (
        b"\x89PNG\r\n\x1a\n"
        + bloque(b"IHDR", struct.pack(">IIBBBBB", ancho, ancho, 8, 2, 0, 0, 0))
        + bloque(b"IDAT", zlib.compress(crudo, 9))
        + bloque(b"IEND", b"")
    )


def icono(lado: int) -> bytes:
    """Un anillo dorado centrado, dentro de la zona segura de un ícono "maskable"."""
    centro = (lado - 1) / 2
    afuera, adentro = lado * 0.30, lado * 0.20
    filas = []
    for y in range(lado):
        fila = bytearray()
        for x in range(lado):
            distancia = ((x - centro) ** 2 + (y - centro) ** 2) ** 0.5
            fila += bytes(ORO if adentro <= distancia <= afuera else AZUL)
        filas.append(bytes(fila))
    return _png(lado, filas)


if __name__ == "__main__":
    DESTINO.mkdir(parents=True, exist_ok=True)
    for lado in (192, 512):
        (DESTINO / f"icono-{lado}.png").write_bytes(icono(lado))
        print(f"icono-{lado}.png")
