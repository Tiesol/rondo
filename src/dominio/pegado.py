"""Leer las listas que la organización pega desde Excel, Word o un PDF pasado a Excel (T7.7).

Cada club manda su lista en un formato distinto (CONTEXTO 6.5). La organización copia las filas
y las pega: llegan como texto separado por tabuladores. Acá se arman las filas, se propone qué
es cada columna (la organización lo puede corregir) y se lee cada fila. Las reglas de
inscripción no se aplican acá: las aplica el mismo servicio que la carga a mano.
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Literal

from dominio.nacimiento import ANIO_MINIMO, Nacimiento, NacimientoInvalido

Columna = Literal[
    "nombres",
    "apellidos",
    "nombre_completo",  # nombres y después apellidos
    "apellidos_nombres",  # apellidos y después nombres
    "nacimiento",
    "documento",
    "dorsal",
    "rol",
    "ignorar",
]
COLUMNAS: dict[Columna, str] = {
    "nombres": "Nombres",
    "apellidos": "Apellidos",
    "nombre_completo": "Nombre completo (nombres primero)",
    "apellidos_nombres": "Nombre completo (apellidos primero)",
    "nacimiento": "Fecha o año de nacimiento",
    "documento": "CI o pasaporte",
    "dorsal": "Dorsal",
    "rol": "Rol",
    "ignorar": "Ignorar",
}
OrdenFechas = Literal["dma", "mda"]
OrdenNombre = Literal["nombres_primero", "apellidos_primero"]


@dataclass(frozen=True)
class FilaLeida:
    numero: int  # 1, 2, 3… en el orden pegado, sin contar el encabezado ni las filas vacías
    nombres: str
    apellidos: str
    nacimiento: Nacimiento | None
    documento: str
    dorsal: int | None
    rol: str | None = None
    errores: tuple[str, ...] = ()


@dataclass(frozen=True)
class Analisis:
    filas: list[list[str]]
    encabezado: list[str] | None
    columnas: list[Columna]
    orden_fechas: OrdenFechas = "dma"
    aviso_fechas: str = ""

    def con_columnas(self, columnas: Sequence[Columna]) -> Analisis:
        """Las columnas que eligió la organización; las fechas se vuelven a mirar."""
        orden, aviso = _orden_de_fechas(self.filas, list(columnas))
        return replace(self, columnas=list(columnas), orden_fechas=orden, aviso_fechas=aviso)


# ---------- Texto ----------


def _normal(texto: str) -> str:
    """Minúsculas, sin acentos ni signos: "Nº DOCUMENTO" → "no documento"."""
    sin_acentos = unicodedata.normalize("NFKD", texto)
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9#]+", " ", sin_acentos.lower()).split())


def _tabla(texto: str) -> list[list[str]]:
    lineas = [linea for linea in texto.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    separador = "\t" if any("\t" in linea for linea in lineas) else None
    if separador is None and any(";" in linea for linea in lineas):
        separador = ";"
    filas = [
        [celda.strip() for celda in (linea.split(separador) if separador else [linea])]
        for linea in lineas
    ]
    filas = [fila for fila in filas if any(fila)]
    if not filas:
        return []
    ancho = max(len(fila) for fila in filas)
    filas = [fila + [""] * (ancho - len(fila)) for fila in filas]
    while ancho and all(not fila[ancho - 1] for fila in filas):
        ancho -= 1
    return [fila[:ancho] for fila in filas]


# ---------- Fechas ----------

_MESES = {
    "enero": 1, "ene": 1, "febrero": 2, "feb": 2, "marzo": 3, "mar": 3, "abril": 4, "abr": 4,
    "mayo": 5, "may": 5, "junio": 6, "jun": 6, "julio": 7, "jul": 7, "agosto": 8, "ago": 8,
    "septiembre": 9, "setiembre": 9, "sep": 9, "sept": 9, "set": 9, "octubre": 10, "oct": 10,
    "noviembre": 11, "nov": 11, "diciembre": 12, "dic": 12,
}  # fmt: skip
_NUMERICA = re.compile(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4}|\d{2})")
_ISO = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
_EN_LETRAS = re.compile(r"(\d{1,2})(?: de | |-|/|\.)([a-z]+)(?: de | |-|/|\.)(\d{4})")
_EXCEL_CERO = date(1899, 12, 30)  # el día 0 de las fechas de Excel (con su 29/02/1900)
_EJEMPLOS = "Se entiende 14/03/2017, 12 de marzo 2014 o solo el año."


def _completa(anio: int, mes: int, dia: int, texto: str) -> Nacimiento:
    if anio < ANIO_MINIMO:
        raise NacimientoInvalido(f"«{texto}» no es una fecha de nacimiento. {_EJEMPLOS}")
    try:
        return Nacimiento.de(date(anio, mes, dia))
    except ValueError:
        raise NacimientoInvalido(f"«{texto}» no es una fecha que exista. {_EJEMPLOS}") from None


def leer_fecha(texto: str, orden: OrdenFechas) -> Nacimiento:
    """Una fecha como llega en las listas: dd/mm/aaaa (o mm/dd si la lista viene así),
    con año corto, aaaa-mm-dd con o sin hora, número de fecha de Excel, el mes en letras
    o solo el año."""
    limpio = texto.strip()
    sin_hora = re.sub(r"\s+\d{1,2}:\d{2}(:\d{2})?$", "", limpio)
    if m := _ISO.fullmatch(sin_hora):
        return _completa(int(m[1]), int(m[2]), int(m[3]), limpio)
    if m := _NUMERICA.fullmatch(sin_hora):
        a, b, anio = int(m[1]), int(m[2]), int(m[3])
        anio += 2000 if len(m[3]) == 2 else 0
        dia, mes = (a, b) if orden == "dma" else (b, a)
        return _completa(anio, mes, dia, limpio)
    m_letras = _EN_LETRAS.fullmatch(_normal(sin_hora))
    if m_letras and (en_letras := _MESES.get(m_letras[2])) is not None:
        return _completa(int(m_letras[3]), en_letras, int(m_letras[1]), limpio)
    if re.fullmatch(r"\d{4}", limpio) and int(limpio) >= ANIO_MINIMO:
        return Nacimiento(int(limpio))
    if re.fullmatch(r"\d{5}", limpio):
        return Nacimiento.de(_EXCEL_CERO + timedelta(days=int(limpio)))
    raise NacimientoInvalido(f"«{limpio}» no es una fecha de nacimiento. {_EJEMPLOS}")


def _orden_de_fechas(filas: list[list[str]], columnas: list[Columna]) -> tuple[OrdenFechas, str]:
    """mm/dd/aaaa solo si alguna fecha lo delata (el segundo número pasa de 12) y ninguna
    dice lo contrario. Si no se puede saber, dd/mm/aaaa, como se escribe en Bolivia."""
    valores = [
        fila[i] for fila in filas for i, c in enumerate(columnas) if c == "nacimiento" and fila[i]
    ]
    pares = [(int(m[1]), int(m[2])) for v in valores if (m := _NUMERICA.fullmatch(v.strip()))]
    if any(a > 12 for a, _ in pares) or not any(b > 12 for _, b in pares):
        return "dma", ""
    ejemplo = next(v for v in valores if (m := _NUMERICA.fullmatch(v.strip())) and int(m[2]) > 12)
    return "mda", (
        f"Las fechas de esta lista vienen como mes/día/año (por ejemplo {ejemplo.strip()}): "
        "se leyeron así, toda la lista."
    )


# ---------- Nombres y roles ----------


def separar_nombre(texto: str, orden: OrdenNombre) -> tuple[str, str]:
    """(nombres, apellidos). Con coma, "APELLIDOS, NOMBRES". Sin coma, los apellidos son las
    dos últimas palabras (o las dos primeras); con dos palabras, una y una."""
    if "," in texto:
        antes, despues = (" ".join(p.split()) for p in texto.split(",", 1))
        return (despues, antes) if orden == "apellidos_primero" else (antes, despues)
    palabras = texto.split()
    if len(palabras) < 2:
        return " ".join(palabras), ""
    cuantos = 2 if len(palabras) > 2 else 1
    if orden == "apellidos_primero":
        return " ".join(palabras[cuantos:]), " ".join(palabras[:cuantos])
    return " ".join(palabras[:-cuantos]), " ".join(palabras[-cuantos:])


_SINONIMOS = {
    "entrenador": {"dt", "director tecnico", "entrenador", "entrenadora", "tecnico", "tecnica",
                   "profe", "profesor", "profesora", "director"},
    "asistente": {"asistente", "asistente tecnico", "at", "ac", "ayudante",
                  "asistente de campo", "auxiliar", "ayudante de campo"},
    "delegado": {"delegado", "delegada", "del", "delegado de equipo"},
}  # fmt: skip


def leer_rol(texto: str, roles: Sequence[str]) -> str | None:
    """El rol del cuerpo técnico escrito de cualquier forma ("D.T", "DT", "Director técnico").
    Solo se proponen los roles de la configuración."""
    clave = _normal(texto)
    compacta = clave.replace(" ", "")
    for rol in roles:
        sinonimos = _SINONIMOS.get(rol, set()) | {_normal(rol)}
        if clave in sinonimos or compacta in {s.replace(" ", "") for s in sinonimos}:
            return rol
    return None


# ---------- Columnas ----------


def _por_encabezado(texto: str) -> Columna | None:
    """Lo que dice el encabezado. None si no se reconoce."""
    t = _normal(texto)
    palabras = set(t.split())
    if palabras & {"telefono", "celular", "cel", "rude", "cat", "categoria", "firma"}:
        return "ignorar"
    if "apellido" in t and "nombre" in t:
        return "apellidos_nombres" if t.index("apellido") < t.index("nombre") else "nombre_completo"
    if "completo" in t or palabras & {"jugador", "jugadores"}:
        return "nombre_completo"
    if "apellido" in t:
        return "apellidos"
    if "nombre" in t:
        return "nombres"
    if palabras & {"documento", "ci", "carnet", "cedula", "pasaporte", "doc"}:
        return "documento"
    if palabras & {"nacimiento", "nac", "fecha", "ano", "anio", "nacido"}:
        return "nacimiento"
    if palabras & {"dorsal", "camiseta", "polera"}:
        return "dorsal"
    if palabras & {"funcion", "rol", "cargo"}:
        return "rol"
    if t in {"n", "no", "nro", "num", "numero", "#", "item", "n o"}:
        return "ignorar"
    return None


def _es_fecha(valor: str) -> bool:
    """Si tiene forma de fecha, aunque no exista (un 31/02 es un error de la fila)."""
    limpio = re.sub(r"\s+\d{1,2}:\d{2}(:\d{2})?$", "", valor.strip())
    if _ISO.fullmatch(limpio) or _NUMERICA.fullmatch(limpio) or re.fullmatch(r"\d{5}", limpio):
        return True
    if (m := _EN_LETRAS.fullmatch(_normal(limpio))) and m[2] in _MESES:
        return True
    return bool(re.fullmatch(r"\d{4}", limpio)) and int(limpio) >= ANIO_MINIMO


def _por_contenido(valores: list[str], roles: Sequence[str]) -> Columna | str:
    """Lo que parece la columna. Para el texto devuelve "texto:<palabras promedio>"."""
    if not valores:
        return "ignorar"

    def mayoria(condicion: list[bool]) -> bool:
        return sum(condicion) >= 0.6 * len(condicion)

    if all(re.fullmatch(r"\d{1,2}", v) for v in valores):
        numeros = [int(v) for v in valores]
        return "ignorar" if numeros == list(range(1, len(numeros) + 1)) else "dorsal"
    if mayoria([_es_fecha(v) for v in valores]):
        return "nacimiento"
    if mayoria([leer_rol(v, roles) is not None for v in valores]):
        return "rol"
    if mayoria([len(re.sub(r"\D", "", v)) >= 5 for v in valores]):
        return "documento"
    if mayoria([bool(re.search(r"[^\W\d_]", v)) for v in valores]):
        return f"texto:{sum(len(v.split()) for v in valores) / len(valores)}"
    return "ignorar"


def _proponer(
    filas: list[list[str]], encabezado: list[str] | None, roles: Sequence[str]
) -> list[Columna]:
    ancho = len(filas[0]) if filas else len(encabezado or [])
    propuestas: list[Columna | str] = []
    for i in range(ancho):
        por_encabezado = _por_encabezado(encabezado[i]) if encabezado else None
        valores = [fila[i] for fila in filas if fila[i]]
        propuestas.append(por_encabezado or _por_contenido(valores, roles))
    textos = [i for i, p in enumerate(propuestas) if p.startswith("texto:")]
    if len(textos) == 1:
        largo = float(str(propuestas[textos[0]]).split(":")[1])
        propuestas[textos[0]] = "nombre_completo" if largo >= 2.5 else "nombres"
    else:
        for orden, i in enumerate(textos):
            propuestas[i] = ("nombres", "apellidos")[orden] if orden < 2 else "ignorar"
    return [p if p in COLUMNAS else "ignorar" for p in propuestas]


def _es_encabezado(fila: list[str]) -> bool:
    reconocidas = [c for c in fila if c and _por_encabezado(c) not in (None, "ignorar")]
    return len(reconocidas) >= 2 and not any(_es_fecha(c) for c in fila if c)


def analizar(texto: str, roles: Sequence[str]) -> Analisis:
    """Las filas pegadas, con el encabezado (si lo hay) y una propuesta de columnas."""
    tabla = _tabla(texto)
    encabezado = tabla[0] if tabla and _es_encabezado(tabla[0]) else None
    filas = tabla[1:] if encabezado else tabla
    columnas = _proponer(filas, encabezado, roles)
    orden, aviso = _orden_de_fechas(filas, columnas)
    return Analisis(filas, encabezado, columnas, orden, aviso)


# ---------- Filas ----------


def leer_filas(analisis: Analisis, roles: Sequence[str]) -> list[FilaLeida]:
    """Cada fila según las columnas elegidas. Lo que no se entiende queda como error de la
    fila, para corregirlo; nada se descarta en silencio."""
    leidas = []
    for numero, fila in enumerate(analisis.filas, start=1):
        datos: dict[str, str] = {"nombres": "", "apellidos": "", "documento": ""}
        nacimiento: Nacimiento | None = None
        dorsal: int | None = None
        rol: str | None = None
        errores: list[str] = []
        for columna, valor in zip(analisis.columnas, fila, strict=False):
            if not valor or columna == "ignorar":
                continue
            match columna:
                case "nombres" | "apellidos" | "documento":
                    datos[columna] = " ".join(valor.split())
                case "nombre_completo" | "apellidos_nombres":
                    orden: OrdenNombre = (
                        "nombres_primero" if columna == "nombre_completo" else "apellidos_primero"
                    )
                    datos["nombres"], datos["apellidos"] = separar_nombre(valor, orden)
                case "nacimiento":
                    try:
                        nacimiento = leer_fecha(valor, analisis.orden_fechas)
                    except NacimientoInvalido as error:
                        errores.append(str(error))
                case "dorsal":
                    limpio = re.sub(r"^(n[º°o]?|#)\s*", "", valor.strip(), flags=re.I)
                    if limpio.isdigit():
                        dorsal = int(limpio)
                    else:
                        errores.append(f"El dorsal «{valor}» no es un número.")
                case "rol":
                    rol = leer_rol(valor, roles)
                    if rol is None:
                        errores.append(
                            f"No se reconoce el rol «{valor}». Tiene que ser {', '.join(roles)}."
                        )
        if not datos["nombres"]:
            errores.append("Faltan los nombres.")
        if not datos["apellidos"]:
            errores.append("Faltan los apellidos.")
        leidas.append(
            FilaLeida(
                numero,
                datos["nombres"],
                datos["apellidos"],
                nacimiento,
                datos["documento"],
                dorsal,
                rol,
                tuple(errores),
            )
        )
    return leidas
