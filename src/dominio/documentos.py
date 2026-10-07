"""INS-04: documentos de identidad normalizados para compararlos (CONTEXTO 4.2).

La organización escribe el CI como venga: "1.234.567 lp", "1234567-1E", "E-1234567" o un
pasaporte. Para saber si una persona ya está en otro equipo se compara una clave hecha con el
número, el complemento y el prefijo "E-". La sigla del departamento se guarda, pero no se
compara (supuesto en PROGRESO.md): es el mismo CI emitido en otro lado.
"""

import re
from dataclasses import dataclass
from typing import Literal

TipoDocumento = Literal["ci", "ci_extranjero", "pasaporte"]

# Siglas de departamento de Bolivia que se escriben junto al CI.
SIGLAS = ("SC", "LP", "CB", "CH", "OR", "PT", "TJ", "BN", "PA")
_SIGLA = "|".join(SIGLAS)

_CI = re.compile(
    rf"^(?P<numero>\d{{4,10}})(?:-(?P<complemento>\d[A-Z]))?(?:-?(?P<sigla>{_SIGLA}))?$"
)
_EXTRANJERO = re.compile(r"^E-?(?P<numero>\d{4,10})$")
_PASAPORTE = re.compile(r"^[A-Z]{1,3}\d{5,10}$")

EJEMPLOS = "1234567 SC, 1234567-1E, E-1234567 o AB123456"


class DocumentoInvalido(ValueError):
    """Un texto con dígitos que no tiene la forma de un CI ni de un pasaporte."""


@dataclass(frozen=True)
class Documento:
    tipo: TipoDocumento
    numero: str
    complemento: str = ""
    sigla: str = ""

    @property
    def clave(self) -> str:
        """Lo que se compara para saber si dos documentos son de la misma persona."""
        if self.tipo == "ci_extranjero":
            return f"E-{self.numero}"
        if self.tipo == "pasaporte":
            return f"P-{self.numero}"
        return f"{self.numero}-{self.complemento}" if self.complemento else self.numero

    @property
    def texto(self) -> str:
        """Cómo se muestra: "1234567-1E SC"."""
        if self.tipo == "ci":
            return f"{self.clave} {self.sigla}".strip()
        return self.clave.removeprefix("P-")


def normalizar_documento(texto: str) -> Documento | None:
    """El documento normalizado, o None si no hay (vacío o sin dígitos, como "S/N").

    Lanza DocumentoInvalido si tiene dígitos pero no se reconoce.
    """
    if not any(caracter.isdigit() for caracter in texto):
        return None
    compacto = re.sub(r"[\s.]", "", texto).upper()

    if coincidencia := _EXTRANJERO.match(compacto):
        return Documento("ci_extranjero", coincidencia["numero"])
    if coincidencia := _CI.match(compacto):
        return Documento(
            "ci",
            coincidencia["numero"],
            coincidencia["complemento"] or "",
            coincidencia["sigla"] or "",
        )
    if _PASAPORTE.match(compacto):
        return Documento("pasaporte", compacto)
    raise DocumentoInvalido(
        f"No se reconoce «{texto.strip()}» como CI ni pasaporte. Ejemplos válidos: {EJEMPLOS}."
    )
