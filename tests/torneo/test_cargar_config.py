"""T1.4: cargar_config crea el torneo 2026 desde el JSON, sin duplicar y sin dejar nada a medias."""

import json
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command

from torneo.models import Cancha, CategoriaNivel, Franja, Torneo

CONFIG_2026 = Path(__file__).resolve().parents[2] / "datos" / "config" / "jmp_cup_2026.json"


def _cargar(ruta: Path = CONFIG_2026) -> str:
    salida = StringIO()
    call_command("cargar_config", str(ruta), stdout=salida)
    return salida.getvalue()


def _codigos(categoria: str, nivel: str) -> set[str]:
    cn = CategoriaNivel.objects.get(categoria=categoria, nivel=nivel)
    return set(cn.canchas.values_list("codigo", flat=True))


@pytest.mark.django_db
def test_crea_el_torneo_2026_completo() -> None:
    _cargar()
    torneo = Torneo.objects.get()
    assert (torneo.nombre, torneo.anio) == ("JMP CUP 2026", 2026)
    assert torneo.categorias.count() == 23
    assert set(torneo.canchas.values_list("codigo", flat=True)) == {"C1", "C1A", "C1B", "C2", "C3"}
    assert Cancha.objects.get(codigo="C1A").padre == Cancha.objects.get(codigo="C1")
    assert torneo.franjas.count() == 15
    assert torneo.reglas == json.loads(CONFIG_2026.read_text())["reglas"]


@pytest.mark.django_db
def test_resuelve_la_compatibilidad_de_canchas() -> None:
    _cargar()
    assert _codigos("Sub 6", "unico") == {"C1A", "C1B"}
    assert _codigos("Sub 10", "avanzado") == {"C1"}
    assert _codigos("Sub 12", "avanzado") == {"C3"}
    assert _codigos("Sub 9", "inicial") == {"C1", "C2"}


@pytest.mark.django_db
def test_cargar_dos_veces_no_duplica_nada() -> None:
    _cargar()
    _cargar()
    assert Torneo.objects.count() == 1
    assert CategoriaNivel.objects.count() == 23
    assert Cancha.objects.count() == 5
    assert Franja.objects.count() == 15


@pytest.mark.django_db
def test_recargar_conserva_las_franjas_agregadas_entre_semana() -> None:
    _cargar()
    Franja.objects.create(
        torneo=Torneo.objects.get(),
        inicio=datetime(2026, 10, 28, 22, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 29, 1, 0, tzinfo=UTC),
        tipo=Franja.Tipo.ENTRE_SEMANA,
    )
    _cargar()
    assert Franja.objects.filter(tipo=Franja.Tipo.ENTRE_SEMANA).count() == 1
    assert Franja.objects.count() == 16


@pytest.mark.django_db
def test_un_json_invalido_no_deja_nada_y_explica_el_error(tmp_path: Path) -> None:
    datos = json.loads(CONFIG_2026.read_text())
    datos["reglas"]["max_partidos_por_dia"] = "dos"
    ruta = tmp_path / "mala.json"
    ruta.write_text(json.dumps(datos))
    with pytest.raises(CommandError, match="max_partidos_por_dia"):
        _cargar(ruta)
    assert not Torneo.objects.exists()
