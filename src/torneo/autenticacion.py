"""Login sin distinguir mayúsculas en el usuario. La contraseña sí las distingue."""

from typing import Any

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.http import HttpRequest


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
