#!/usr/bin/env python
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))


def main() -> None:
    from rondo.entorno import cargar_env

    # RONDO_ENV_FILE vacío desactiva la carga (lo usan los tests).
    archivo = os.environ.get("RONDO_ENV_FILE", str(RAIZ / ".env"))
    if archivo:
        cargar_env(Path(archivo))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rondo.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
