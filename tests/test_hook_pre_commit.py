"""El hook antes del commit rechaza listas reales y secretos (SPEC, "Límites")."""

import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "scripts" / "hooks" / "pre-commit"


def _repo_con(tmp_path: Path, archivo: str) -> subprocess.CompletedProcess[str]:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / archivo).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / archivo).write_text("contenido")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-f", archivo], check=True)
    destino = tmp_path / ".git" / "hooks" / "pre-commit"
    shutil.copy(HOOK, destino)
    return subprocess.run([str(destino)], cwd=tmp_path, capture_output=True, text=True, check=False)


@pytest.mark.parametrize(
    "archivo",
    [
        "lista_sub9.xlsx",
        "lista.XLS",
        "plantel.docx",
        "lista.pdf",
        "foto.jpg",
        ".env",
        "config/.env.produccion",
    ],
)
def test_rechaza_archivos_prohibidos(tmp_path: Path, archivo: str) -> None:
    resultado = _repo_con(tmp_path, archivo)
    assert resultado.returncode != 0
    assert archivo in resultado.stderr


def test_deja_pasar_el_archivo_de_ejemplo_del_entorno(tmp_path: Path) -> None:
    resultado = _repo_con(tmp_path, ".env.example")
    assert resultado.returncode == 0, resultado.stderr
