"""El hook antes del commit rechaza listas reales y secretos (SPEC, "Límites")."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "scripts" / "hooks" / "pre-commit"


def _repo_con(tmp_path: Path, archivo: str) -> subprocess.CompletedProcess[str]:
    # Sin las variables GIT_* del commit que está corriendo estos tests (GIT_INDEX_FILE,
    # GIT_DIR…): si no, el repo de prueba escribe en el índice del repo de verdad.
    entorno = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, env=entorno)
    (tmp_path / archivo).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / archivo).write_text("contenido")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-f", archivo], check=True, env=entorno)
    destino = tmp_path / ".git" / "hooks" / "pre-commit"
    shutil.copy(HOOK, destino)
    return subprocess.run(
        [str(destino)], cwd=tmp_path, capture_output=True, text=True, check=False, env=entorno
    )


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


def test_no_toca_el_indice_del_repo_que_esta_haciendo_el_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Estos tests corren dentro del hook. Ahí git exporta GIT_INDEX_FILE; desde un worktree
    es una ruta absoluta, y el repo de prueba escribía en el índice del repo de verdad."""
    ajeno = tmp_path / "ajeno" / "index"
    ajeno.parent.mkdir()
    monkeypatch.setenv("GIT_INDEX_FILE", str(ajeno))
    resultado = _repo_con(tmp_path / "repo", "lista_sub9.xlsx")
    assert resultado.returncode != 0
    assert not ajeno.exists()
