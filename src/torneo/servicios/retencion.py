"""Retención de datos (T6.4, P49): un torneo terminado se queda sin datos personales.

Por defecto de P49, se corre a fin de año. Quedan los planteles como "Jugador 1, 2…" con su
dorsal, y los equipos, partidos y calendario intactos. Las fotos se borran del almacenamiento
(T9.1, P76). A quien también esté en otro torneo no
se lo toca: sus datos siguen haciendo falta ahí.
"""

from django.db import transaction
from django.utils import timezone

from torneo.models import Equipo, Jugador, Persona, Profe, Torneo


class NoSePuedeAnonimizar(Exception):
    pass


@transaction.atomic
def anonimizar(torneo: Torneo) -> int:
    """Cuántas personas quedaron sin datos personales."""
    if torneo.fin >= timezone.localdate():
        raise NoSePuedeAnonimizar(
            f"{torneo} todavía no terminó (termina el {torneo.fin:%d/%m/%Y}): no se anonimiza."
        )
    # Quien también está en otro torneo conserva sus datos: allá siguen haciendo falta.
    quedan = set(
        Jugador.objects.exclude(equipo__categoria__torneo=torneo).values_list(
            "persona_id", flat=True
        )
    ) | set(
        Profe.objects.exclude(equipo__categoria__torneo=torneo).values_list("persona_id", flat=True)
    )

    nuevos: dict[int, tuple[str, str]] = {}
    for equipo in Equipo.objects.filter(categoria__torneo=torneo).prefetch_related(
        "jugadores", "profes"
    ):
        jugadores = sorted(equipo.jugadores.all(), key=lambda j: (j.dorsal or 999, j.pk))
        for numero, jugador in enumerate(jugadores, start=1):
            nuevos.setdefault(jugador.persona_id, ("Jugador", str(numero)))
        for numero, profe in enumerate(equipo.profes.all(), start=1):
            nuevos.setdefault(profe.persona_id, ("Profe", str(numero)))

    personas = [p for p in Persona.objects.filter(pk__in=nuevos) if p.pk not in quedan]
    fotos = [p.foto.name for p in personas if p.foto.name]
    for persona in personas:
        persona.nombres, persona.apellidos = nuevos[persona.pk]
        persona.tipo_documento = persona.documento = persona.clave_documento = ""
        persona.nacido = None
        # T9.1 (P49, P76): la foto también es un dato personal; sale del almacenamiento.
        persona.foto = ""
        persona.foto_autorizada = False
        persona.foto_autorizada_por = None
        persona.foto_autorizada_en = None
    Persona.objects.bulk_update(
        personas,
        [
            "nombres",
            "apellidos",
            "tipo_documento",
            "documento",
            "clave_documento",
            "anio_nacimiento",
            "nacimiento",
            "foto",
            "foto_autorizada",
            "foto_autorizada_por",
            "foto_autorizada_en",
        ],
    )
    # Los archivos se borran recién cuando la base confirma: si algo falla, no se pierden.
    almacenamiento = Persona._meta.get_field("foto").storage

    def borrar_fotos() -> None:
        for nombre in fotos:
            almacenamiento.delete(nombre)

    transaction.on_commit(borrar_fotos)
    return len(personas)
