"""Canchas compatibles con cada categoría-nivel (CAT-04) y canchas físicas que ocupa cada una."""

from dominio.config import ConfigTorneo


def canchas_fisicas(config: ConfigTorneo) -> dict[str, frozenset[str]]:
    """Cancha que se elige → canchas físicas que ocupa. Una entera ocupa sus mitades (PRO-01)."""
    fisicas: dict[str, frozenset[str]] = {}
    for cancha in config.canchas:
        if cancha.mitades:
            fisicas[cancha.codigo] = frozenset(cancha.mitades)
            for mitad in cancha.mitades:
                fisicas[mitad] = frozenset({mitad})
        else:
            fisicas[cancha.codigo] = frozenset({cancha.codigo})
    return fisicas


def canchas_compatibles(config: ConfigTorneo, categoria: str, nivel: str) -> tuple[str, ...]:
    """La regla por categoría manda sobre la de modalidad (CAT-04)."""
    niveles = {str(clave): datos for clave, datos in config.categoria(categoria).niveles.items()}
    if nivel not in niveles:
        raise KeyError(f"{categoria} no tiene el nivel {nivel}")
    por_categoria = config.compatibilidad.por_categoria.get(categoria)
    if por_categoria is not None:
        return por_categoria
    return config.compatibilidad.por_modalidad.get(niveles[nivel].modalidad, ())
