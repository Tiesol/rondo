"""Carga un archivo .env para desarrollo local. En la nube, las variables vienen del entorno."""

import os
from pathlib import Path


def cargar_env(archivo: Path) -> None:
    """Define las variables de `archivo` (líneas CLAVE=valor) sin pisar las que ya existen."""
    if not archivo.is_file():
        return
    for linea in archivo.read_text().splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip())
