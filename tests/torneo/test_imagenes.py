"""T8.2: al subir una imagen se achica, se pasa a WebP y se le borran los metadatos.

Son fotos de menores: el EXIF puede traer la ubicación GPS de la casa. Imágenes inventadas,
generadas en memoria.
"""

import io

import pytest
from PIL import Image

from torneo.servicios.imagenes import ImagenInvalida, procesar_imagen

GPS = 0x8825
ORIENTACION = 0x0112


def jpeg(ancho: int = 1600, alto: int = 1200, *, gps: bool = False, girada: bool = False) -> bytes:
    imagen = Image.new("RGB", (ancho, alto), (200, 30, 40))
    exif = Image.Exif()
    exif[0x010F] = "Telefono inventado"  # marca de la cámara
    if gps:
        exif.get_ifd(GPS).update({1: "S", 2: (17.0, 47.0, 0.0), 3: "W", 4: (63.0, 10.0, 0.0)})
    if girada:
        exif[ORIENTACION] = 6  # el teléfono estaba de costado
    salida = io.BytesIO()
    imagen.save(salida, "JPEG", exif=exif)
    return salida.getvalue()


def abrir(contenido: bytes) -> Image.Image:
    return Image.open(io.BytesIO(contenido))


def test_una_foto_con_gps_sale_sin_ningun_metadato() -> None:
    original = jpeg(gps=True)
    assert abrir(original).getexif().get_ifd(GPS)  # el original sí tiene la ubicación
    resultado = procesar_imagen(io.BytesIO(original), tipo="foto")
    imagen = abrir(resultado.read())
    assert imagen.format == "WEBP"
    assert len(imagen.getexif()) == 0
    assert not {"exif", "xmp", "icc_profile"} & set(imagen.info)


@pytest.mark.parametrize(("tipo", "lado"), [("foto", 800), ("escudo", 400), ("logo", 400)])
def test_se_achica_al_tamano_de_su_tipo(tipo: str, lado: int) -> None:
    imagen = abrir(procesar_imagen(io.BytesIO(jpeg(3000, 2000)), tipo=tipo).read())  # type: ignore[arg-type]
    assert max(imagen.size) == lado
    assert imagen.size[0] / imagen.size[1] == pytest.approx(1.5, rel=0.01)


def test_una_imagen_chica_no_se_agranda() -> None:
    imagen = abrir(procesar_imagen(io.BytesIO(jpeg(300, 200)), tipo="foto").read())
    assert imagen.size == (300, 200)


def test_la_orientacion_del_telefono_se_aplica_antes_de_borrar_el_exif() -> None:
    imagen = abrir(procesar_imagen(io.BytesIO(jpeg(1600, 1200, girada=True)), tipo="foto").read())
    assert imagen.size == (600, 800)  # quedó parada, como se veía en el teléfono


def test_un_escudo_con_transparencia_la_conserva() -> None:
    png = io.BytesIO()
    Image.new("RGBA", (500, 500), (0, 0, 0, 0)).save(png, "PNG")
    imagen = abrir(procesar_imagen(io.BytesIO(png.getvalue()), tipo="escudo").read())
    assert imagen.mode == "RGBA"


def test_el_nombre_es_al_azar_y_sin_datos_de_la_persona() -> None:
    subido = io.BytesIO(jpeg())
    subido.name = "Juan Perez.jpg"  # como llega del formulario
    uno = procesar_imagen(subido, tipo="foto")
    otro = procesar_imagen(io.BytesIO(jpeg()), tipo="foto")
    assert uno.name is not None and uno.name != otro.name
    assert uno.name.startswith("fotos/") and uno.name.endswith(".webp")
    assert "juan" not in uno.name.lower() and "perez" not in uno.name.lower()


@pytest.mark.parametrize(
    "contenido",
    [b"esto no es una imagen", b"%PDF-1.4 inventado", b"GIF89a" + b"\x00" * 30],
)
def test_lo_que_no_es_una_imagen_permitida_se_rechaza(contenido: bytes) -> None:
    with pytest.raises(ImagenInvalida, match="JPG, PNG o WebP"):
        procesar_imagen(io.BytesIO(contenido), tipo="foto")


def test_un_archivo_que_pasa_el_maximo_se_rechaza(settings: object) -> None:
    settings.IMAGEN_MAX_MB = 1  # type: ignore[attr-defined]
    with pytest.raises(ImagenInvalida, match="1 MB"):
        procesar_imagen(io.BytesIO(b"\xff\xd8" + b"\x00" * (1024 * 1024 + 1)), tipo="foto")


def test_una_imagen_gigante_en_pixeles_se_rechaza() -> None:
    enorme = io.BytesIO()
    Image.new("L", (12000, 12000)).save(enorme, "PNG")  # pesa poco, pero son 144 MP
    with pytest.raises(ImagenInvalida, match="grande"):
        procesar_imagen(io.BytesIO(enorme.getvalue()), tipo="foto")
