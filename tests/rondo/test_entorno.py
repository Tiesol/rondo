import os
from pathlib import Path

import pytest

from rondo.entorno import cargar_env


def test_carga_las_variables_del_archivo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RONDO_PRUEBA_A", raising=False)
    archivo = tmp_path / ".env"
    archivo.write_text("# comentario\n\nRONDO_PRUEBA_A=valor con espacios\n")

    cargar_env(archivo)

    assert os.environ["RONDO_PRUEBA_A"] == "valor con espacios"


def test_no_pisa_una_variable_que_ya_existe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RONDO_PRUEBA_B", "del entorno")
    archivo = tmp_path / ".env"
    archivo.write_text("RONDO_PRUEBA_B=del archivo\n")

    cargar_env(archivo)

    assert os.environ["RONDO_PRUEBA_B"] == "del entorno"


def test_si_el_archivo_no_existe_no_hace_nada(tmp_path: Path) -> None:
    cargar_env(tmp_path / "no-existe.env")
