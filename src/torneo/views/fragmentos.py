from django.http import HttpRequest


def pide_fragmento(request: HttpRequest) -> bool:
    """HTMX pide solo la parte que cambia, salvo al restaurar el historial del navegador:
    ahí espera la página entera."""
    htmx = getattr(request, "htmx", None)
    return bool(htmx) and not htmx.history_restore_request  # type: ignore[union-attr]
