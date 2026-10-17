"""T13.43: subir una foto grande no puede llevar el proceso a los 512 MB de Render Free.

Medido con la imagen limitada como Render: después de programar, el worker queda en unos 260 MB;
una foto de 40 MP sumaba +313 MB al procesarla (cada copia a tamaño completo son 120 MB) y un
escudo PNG de 40 MP, +343 MB, aunque el archivo pesaba 0,2 MB. Ahora un JPEG se decodifica ya
achicado (`draft`) y lo demás se achica apenas se abre (`reduce`).

Cada medición corre en un proceso aparte: el pico de memoria (ru_maxrss) es por proceso.
"""

import io
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from torneo.servicios.imagenes import ImagenInvalida, procesar_imagen, tiene_fondo

RAIZ = Path(__file__).resolve().parents[2]
ANCHO, ALTO = 7296, 5472  # 40 MP
LADO_PNG = 5000  # 25 MP


@pytest.fixture(scope="module")
def fotos(tmp_path_factory: pytest.TempPathFactory) -> Path:
    carpeta = tmp_path_factory.mktemp("fotos")
    # Una foto de teléfono: 40 MP, girada en el EXIF (orientación 6) y de menos de 8 MB.
    chica = Image.linear_gradient("L").resize((ANCHO // 8, ALTO // 8))
    ruido = Image.effect_noise((ANCHO // 8, ALTO // 8), 40)
    base = Image.merge("RGB", (chica, ruido, chica.rotate(90))).resize((ANCHO, ALTO))
    exif = Image.Exif()
    exif[0x0112] = 6
    base.save(carpeta / "foto.jpg", "JPEG", quality=85, exif=exif)
    del base
    # Un escudo PNG con transparencia, del máximo que se acepta (25 MP): pesa poco en disco y
    # mucho decodificado.
    escudo = Image.new("RGBA", (LADO_PNG, LADO_PNG), (0, 0, 0, 0))
    ImageDraw.Draw(escudo).ellipse((500, 500, LADO_PNG - 500, LADO_PNG - 500), fill=(20, 60, 160))
    escudo.save(carpeta / "escudo.png")
    return carpeta


def _megas_al_procesar(ruta: Path, tipo: str) -> float:
    """Cuánto sube el pico de memoria del proceso al procesar la imagen, como al subirla."""
    codigo = f"""
import os, resource, django
django.setup()
from torneo.servicios.imagenes import ImagenInvalida, procesar_imagen, tiene_fondo
antes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
with open({str(ruta)!r}, "rb") as f:
    if {tipo!r} == "escudo":
        tiene_fondo(f)
    procesar_imagen(f, tipo={tipo!r})
print((resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - antes) / 1024)
"""
    entorno = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME"}} | {
        "PYTHONPATH": str(RAIZ / "src"),
        "DJANGO_SETTINGS_MODULE": "rondo.settings",
        "SECRET_KEY": "solo-tests",
        "DEBUG": "true",
        "DATABASE_URL": "postgres://rondo:rondo@localhost:5432/rondo",
    }
    resultado = subprocess.run(
        [sys.executable, "-c", codigo], env=entorno, capture_output=True, text=True, check=False
    )
    assert resultado.returncode == 0, resultado.stderr
    return float(resultado.stdout.strip().splitlines()[-1])


def test_una_foto_de_40_mp_no_se_decodifica_entera(fotos: Path) -> None:
    assert _megas_al_procesar(fotos / "foto.jpg", "foto") < 60


def test_un_escudo_jpg_de_40_mp_tampoco(fotos: Path) -> None:
    assert _megas_al_procesar(fotos / "foto.jpg", "escudo") < 60


def _tamanos_de_las_copias(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Los píxeles de cada imagen que se copia (convertir, sacar el canal alfa o girar)."""
    copias: list[int] = []
    for nombre in ("convert", "getchannel", "transpose", "copy"):
        original = getattr(Image.Image, nombre)

        def espia(self: Image.Image, *a: object, _o: object = original, **k: object) -> object:
            copias.append(self.width * self.height)
            return _o(self, *a, **k)  # type: ignore[operator]

        monkeypatch.setattr(Image.Image, nombre, espia)
    return copias


def test_un_escudo_png_grande_se_achica_antes_de_copiarlo(
    fotos: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Un PNG no se puede decodificar achicado: se achica apenas se abre, antes de cualquier
    # copia. Antes: tiene_fondo lo convertía entero a RGBA (160 MB), y procesar_imagen, otra vez.
    copias = _tamanos_de_las_copias(monkeypatch)
    with open(fotos / "escudo.png", "rb") as f:
        tiene_fondo(f)
        procesar_imagen(f, tipo="escudo")
    assert copias and max(copias) <= LADO_PNG * LADO_PNG // 8  # ninguna copia de más de 1/8


def test_la_foto_achicada_sigue_derecha_y_del_tamano_de_siempre(fotos: Path) -> None:
    with open(fotos / "foto.jpg", "rb") as f:
        salida = procesar_imagen(f, tipo="foto")
    imagen = Image.open(io.BytesIO(salida.read()))
    # Girada por el EXIF: queda vertical, con el lado mayor de 800 px.
    assert imagen.size == (600, 800)


def test_un_png_de_mas_de_25_mp_se_rechaza() -> None:
    # Un PNG o un WebP no se puede decodificar achicado: 40 MP con transparencia son 160 MB y,
    # después de programar, el proceso llegaba a unos 450 MB. Las fotos de teléfono son JPEG.
    archivo = io.BytesIO()
    Image.new("RGBA", (6000, 5000), (0, 0, 0, 0)).save(archivo, "PNG")
    archivo.seek(0)
    with pytest.raises(ImagenInvalida, match="demasiado grande"):
        procesar_imagen(archivo, tipo="escudo")


def test_un_jpg_de_40_mp_se_sigue_aceptando(fotos: Path) -> None:
    with open(fotos / "foto.jpg", "rb") as f:
        assert procesar_imagen(f, tipo="escudo").size > 0
