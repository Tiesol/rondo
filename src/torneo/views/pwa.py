"""Instalación en el celular (T5.8): manifest y service worker.

Se sirven sin login (los navegadores los piden sin la sesión) y no tienen datos personales.
La app funciona solo con conexión (decisión del 2026-10-06): el service worker no guarda
nada; si no hay red, muestra un aviso.
"""

from django.contrib.auth.decorators import login_not_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.templatetags.static import static

from torneo.models import Organizador

SERVICE_WORKER = """// Rondo: sin datos guardados en el teléfono. Si no hay red, un aviso.
const SIN_CONEXION = `<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sin conexión</title>
<body style="font-family: system-ui, sans-serif; padding: 24px; text-align: center">
<h1>Sin conexión</h1><p>Rondo necesita internet. Vuelve a intentar cuando tengas señal.</p>
</body></html>`;

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (evento) => evento.waitUntil(self.clients.claim()));
self.addEventListener("fetch", (evento) => {
  if (evento.request.mode !== "navigate") return;
  evento.respondWith(
    fetch(evento.request).catch(
      () => new Response(SIN_CONEXION, { headers: { "Content-Type": "text/html; charset=utf-8" } })
    )
  );
});
"""


@login_not_required
def manifest(request: HttpRequest) -> JsonResponse:
    organizador = Organizador.actual()
    return JsonResponse(
        {
            "name": f"Rondo · {organizador.nombre}",
            "short_name": "Rondo",
            "lang": "es",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": organizador.color_primario,
            "theme_color": organizador.color_primario,
            "icons": [
                {
                    "src": static(f"iconos/icono-{lado}.png"),
                    "sizes": f"{lado}x{lado}",
                    "type": "image/png",
                    "purpose": "any maskable",
                }
                for lado in (192, 512)
            ],
        },
        content_type="application/manifest+json",
        json_dumps_params={"ensure_ascii": False},
    )


@login_not_required
def service_worker(request: HttpRequest) -> HttpResponse:
    respuesta = HttpResponse(SERVICE_WORKER, content_type="application/javascript")
    respuesta["Cache-Control"] = "no-cache"
    return respuesta
