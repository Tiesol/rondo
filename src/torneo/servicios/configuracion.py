"""Pasa una configuración validada por el dominio a la base (T1.4)."""

from django.db import transaction

from dominio.canchas import canchas_compatibles
from dominio.config import ConfigTorneo
from dominio.franjas import franjas_del_torneo
from torneo.models import Cancha, CategoriaNivel, Franja, Torneo


@transaction.atomic
def cargar_configuracion(config: ConfigTorneo) -> Torneo:
    """Crea o actualiza el torneo con todas sus tablas. Es idempotente y va en una transacción.

    No borra categorías ni canchas que ya no estén en el JSON: podrían tener equipos o partidos.
    Las franjas regulares se regeneran; las de entre semana (para reprogramar) se conservan.
    """
    torneo, _ = Torneo.objects.update_or_create(
        nombre=config.torneo.nombre,
        anio=config.torneo.anio,
        defaults={
            "edicion": config.torneo.edicion,
            "inicio": config.torneo.inicio,
            "fin": config.torneo.fin,
            "zona_horaria": config.torneo.zona_horaria,
            "descanso_min": config.partido.descanso_min,
            "cambio_entre_partidos_min": config.partido.cambio_entre_partidos_min,
            "cuerpo_tecnico": config.cuerpo_tecnico.model_dump(mode="json"),
            "reglas": config.reglas.model_dump(mode="json"),
        },
    )

    canchas: dict[str, Cancha] = {}
    for cancha in config.canchas:
        entera, _ = Cancha.objects.update_or_create(
            torneo=torneo, codigo=cancha.codigo, defaults={"nombre": cancha.nombre, "padre": None}
        )
        canchas[cancha.codigo] = entera
        for mitad in cancha.mitades:
            canchas[mitad], _ = Cancha.objects.update_or_create(
                torneo=torneo,
                codigo=mitad,
                defaults={
                    "nombre": f"{cancha.nombre} {mitad.removeprefix(cancha.codigo)}",
                    "padre": entera,
                },
            )

    for categoria in config.categorias:
        for nombre_nivel, nivel in categoria.niveles.items():
            categoria_nivel, _ = CategoriaNivel.objects.update_or_create(
                torneo=torneo,
                categoria=categoria.nombre,
                nivel=nombre_nivel,
                defaults={
                    "edad": categoria.edad,
                    "anios_nacimiento": categoria.anios_nacimiento,
                    "genero": categoria.genero,
                    "modalidad": nivel.modalidad,
                    "min_jugadores": nivel.min,
                    "max_jugadores": nivel.max,
                    "min_por_tiempo": nivel.min_por_tiempo,
                    "convocados_por_partido": nivel.convocados_por_partido,
                },
            )
            compatibles = canchas_compatibles(config, categoria.nombre, nombre_nivel)
            categoria_nivel.canchas.set([canchas[codigo] for codigo in compatibles])

    torneo.franjas.filter(tipo=Franja.Tipo.REGULAR).delete()
    Franja.objects.bulk_create(
        Franja(torneo=torneo, inicio=f.inicio, fin=f.fin, tipo=Franja.Tipo.REGULAR)
        for f in franjas_del_torneo(config)
    )
    return torneo
