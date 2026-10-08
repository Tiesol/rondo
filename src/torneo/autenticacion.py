"""Login sin distinguir mayúsculas en el usuario (la contraseña sí), y con límite de intentos."""

from typing import Any

from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse


class UsuarioSinMayusculasBackend(ModelBackend):
    def authenticate(
        self,
        request: HttpRequest | None,
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> User | None:
        if username and username.strip():
            guardado = (
                User.objects.filter(username__iexact=username.strip())
                .values_list("username", flat=True)
                .first()
            )
            username = guardado or username
        return super().authenticate(request, username=username, password=password, **kwargs)


class VistaDeIngreso(LoginView):
    """El login con límite de intentos fallidos (T6.3): por IP y por usuario, en una ventana.

    Pasado el límite, ni la contraseña correcta entra hasta que pase la ventana: así no
    sirve probar claves a ciegas.
    """

    redirect_authenticated_user = True

    def _claves(self) -> list[str]:
        usuario = (self.request.POST.get("username") or "").strip().lower()
        reenviada = self.request.META.get("HTTP_X_FORWARDED_FOR", "")
        # Detrás del proxy de Render, la IP real es la última que agrega el proxy.
        ip = (
            reenviada.split(",")[-1].strip()
            if reenviada
            else self.request.META.get("REMOTE_ADDR", "")
        )
        return [f"login:ip:{ip}", f"login:usuario:{usuario}"]

    def _bloqueado(self) -> bool:
        return any(cache.get(c, 0) >= settings.LOGIN_MAX_INTENTOS for c in self._claves())

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if self._bloqueado():
            contexto = self.get_context_data(form=self.form_class(request), bloqueado=True)
            return self.render_to_response(contexto, status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form: Any) -> HttpResponse:
        for clave in self._claves():
            cache.add(clave, 0, settings.LOGIN_VENTANA_SEGUNDOS)
            cache.incr(clave)
        return super().form_invalid(form)
