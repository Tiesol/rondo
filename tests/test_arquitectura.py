"""El dominio es Python puro: no importa Django ni la app web (ARQUITECTURA, sección 1)."""

import ast
from pathlib import Path

DOMINIO = Path(__file__).resolve().parents[1] / "src" / "dominio"
PROHIBIDOS = {"django", "torneo", "rondo"}


def _modulos_importados(archivo: Path) -> set[str]:
    arbol = ast.parse(archivo.read_text(), filename=str(archivo))
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(alias.name.split(".")[0] for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            nombres.add(nodo.module.split(".")[0])
    return nombres


def test_el_paquete_dominio_existe() -> None:
    assert (DOMINIO / "__init__.py").is_file()


def test_el_dominio_no_importa_django_ni_la_app() -> None:
    infracciones = {
        str(archivo.relative_to(DOMINIO)): sorted(_modulos_importados(archivo) & PROHIBIDOS)
        for archivo in DOMINIO.rglob("*.py")
        if _modulos_importados(archivo) & PROHIBIDOS
    }
    assert infracciones == {}
