"""Crea un usuario de la organización. La contraseña sale de RONDO_CLAVE_USUARIO y no se muestra."""

import os
from typing import Any

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

VARIABLE = "RONDO_CLAVE_USUARIO"


class Command(BaseCommand):
    help = f"Crea un usuario staff (o administrador con --admin). La contraseña sale de {VARIABLE}."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("usuario")
        parser.add_argument("--email", default="")
        parser.add_argument("--admin", action="store_true", help="Superusuario: acceso total")

    def handle(self, *args: Any, **opciones: Any) -> None:
        clave = os.environ.get(VARIABLE, "")
        if not clave:
            raise CommandError(f"Falta la variable de entorno {VARIABLE} con la contraseña.")

        nombre = opciones["usuario"].strip().lower()
        if User.objects.filter(username__iexact=nombre).exists():
            raise CommandError(f"El usuario «{nombre}» ya existe.")

        usuario = User(username=nombre, email=opciones["email"])
        try:
            validate_password(clave, usuario)
        except ValidationError as error:
            raise CommandError("La contraseña no es segura: " + " ".join(error.messages)) from None

        with transaction.atomic():
            usuario.is_staff = True
            usuario.is_superuser = opciones["admin"]
            usuario.set_password(clave)
            usuario.save()
        self.stdout.write(self.style.SUCCESS(f"Usuario «{usuario.username}» creado."))
