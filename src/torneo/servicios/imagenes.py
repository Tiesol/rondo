"""Procesar una imagen al subirla (T8.2): solo imágenes, achicadas, en WebP y sin metadatos.

Son fotos de menores: el EXIF de un teléfono puede traer la ubicación GPS de donde se sacó.
La imagen se vuelve a dibujar en una nueva, sin nada más que los píxeles, así no pasa ningún
metadato (EXIF, XMP ni perfil de color). El nombre del archivo es al azar.
"""

import io
import uuid
import warnings
from typing import IO, Literal

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models.fields.files import FieldFile
from PIL import Image, ImageOps, UnidentifiedImageError

Tipo = Literal["foto", "escudo", "logo", "patrocinador"]
# El lado mayor, en píxeles: una foto se ve en el celular; un escudo o un logo, más chico.
LADO: dict[Tipo, int] = {"foto": 800, "escudo": 400, "logo": 400, "patrocinador": 400}
CARPETA: dict[Tipo, str] = {
    "foto": "fotos",
    "escudo": "escudos",
    "logo": "logos",
    "patrocinador": "patrocinadores",
}
FORMATOS = {"JPEG", "PNG", "WEBP"}
MAX_PIXELES = 40_000_000  # una foto de teléfono tiene 12 a 50 MP; más es sospechoso
_PERMITIDOS = "Tiene que ser una imagen JPG, PNG o WebP."


class ImagenInvalida(ValueError):
    """El archivo no es una imagen que se pueda subir; el mensaje dice por qué."""


def procesar_imagen(archivo: IO[bytes], *, tipo: Tipo) -> ContentFile[bytes]:
    """La imagen lista para guardar, con un nombre al azar (nunca el del archivo subido)."""
    maximo = settings.IMAGEN_MAX_MB * 1024 * 1024
    contenido = archivo.read(maximo + 1)
    if len(contenido) > maximo:
        raise ImagenInvalida(f"La imagen pesa más de {settings.IMAGEN_MAX_MB} MB.")
    imagen = _abrir(contenido)
    imagen = ImageOps.exif_transpose(imagen)  # como se veía en el teléfono, antes de borrar
    transparente = imagen.mode in ("RGBA", "LA", "P") and tipo != "foto"
    modo = "RGBA" if transparente else "RGB"
    imagen = imagen.convert(modo)
    imagen.thumbnail((LADO[tipo], LADO[tipo]), Image.Resampling.LANCZOS)

    limpia = Image.new(modo, imagen.size)
    limpia.paste(imagen)
    salida = io.BytesIO()
    limpia.save(salida, "WEBP", quality=82, method=4)
    return ContentFile(salida.getvalue(), name=f"{CARPETA[tipo]}/{uuid.uuid4().hex}.webp")


def _abrir(contenido: bytes) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            prueba = Image.open(io.BytesIO(contenido))
            if prueba.format not in FORMATOS:
                raise ImagenInvalida(_PERMITIDOS)
            if prueba.width * prueba.height > MAX_PIXELES:
                raise ImagenInvalida("La imagen es demasiado grande: achícala antes de subirla.")
            prueba.verify()  # revisa que el archivo no esté roto
            imagen = Image.open(io.BytesIO(contenido))
            imagen.load()
            return imagen
    except Image.DecompressionBombWarning, Image.DecompressionBombError:
        raise ImagenInvalida("La imagen es demasiado grande: achícala antes de subirla.") from None
    except UnidentifiedImageError, OSError, SyntaxError:
        raise ImagenInvalida(_PERMITIDOS) from None


class SinAlmacenamiento(ImagenInvalida):
    """No hay dónde guardar imágenes: falta conectar R2 (T8.1)."""


def reemplazar_imagen(
    campo: FieldFile, archivo: IO[bytes], *, tipo: Tipo, borrar_anterior: bool = True
) -> None:
    """Procesa la imagen, la guarda en el campo y borra la anterior (no quedan huérfanas), salvo
    que otro la siga usando (`borrar_anterior=False`)."""
    if not settings.IMAGENES_DISPONIBLES:
        raise SinAlmacenamiento("Falta conectar el almacenamiento de imágenes.")
    nueva = procesar_imagen(archivo, tipo=tipo)
    anterior = campo.name
    assert nueva.name is not None
    campo.save(nueva.name, nueva, save=True)
    if anterior and borrar_anterior:
        campo.storage.delete(anterior)


def quitar_imagen(campo: FieldFile, *, borrar: bool = True) -> None:
    """Saca la imagen del campo y borra el archivo, salvo que otro lo siga usando."""
    if not campo.name:
        return
    if borrar:
        campo.delete(save=True)
    else:
        campo.name = ""
        assert campo.instance is not None
        campo.instance.save(update_fields=[campo.field.name])


def tiene_fondo(archivo: IO[bytes]) -> bool:
    """T13.30: si el escudo tiene fondo (sin transparencia en los bordes): un JPG, o un PNG con
    el recuadro pintado. No cambia la posición del archivo. Si no se puede leer, False: la
    validación de verdad la hace procesar_imagen."""
    inicio = archivo.tell()
    try:
        imagen = Image.open(archivo)
        imagen.load()
    except UnidentifiedImageError, OSError, SyntaxError:
        return False
    finally:
        archivo.seek(inicio)
    if imagen.mode not in ("RGBA", "LA") and "transparency" not in imagen.info:
        return True
    alfa = imagen.convert("RGBA").getchannel("A")
    ancho, alto = alfa.size
    borde = (
        [alfa.getpixel((x, 0)) for x in range(ancho)]
        + [alfa.getpixel((x, alto - 1)) for x in range(ancho)]
        + [alfa.getpixel((0, y)) for y in range(alto)]
        + [alfa.getpixel((ancho - 1, y)) for y in range(alto)]
    )
    opacos = sum(1 for a in borde if isinstance(a, int) and a > 200)
    return opacos > 0.9 * len(borde)
