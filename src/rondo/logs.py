"""Logs sin datos personales (revisión de la fase 0).

Los errores de Postgres traen los valores en el texto: una violación de unicidad del CI deja
"Key (clave_documento)=(…) already exists". Este filtro saca el detalle de cualquier error
de la base (y de los errores encadenados) y deja solo su tipo.
"""

import logging

from django.db import DatabaseError

OCULTO = "detalle oculto: puede tener datos personales"


def _viene_de_la_base(error: BaseException | None) -> bool:
    while error is not None:
        if isinstance(error, DatabaseError) or type(error).__module__.startswith("psycopg"):
            return True
        error = error.__cause__ or error.__context__
    return False


class SinDatosDeLaBase(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info and _viene_de_la_base(record.exc_info[1]):
            tipo = record.exc_info[0].__name__ if record.exc_info[0] else "Error"
            record.msg = f"{record.getMessage()} [{tipo}: {OCULTO}]"
            record.args = None
            record.exc_info = None
            record.exc_text = None
        return True
