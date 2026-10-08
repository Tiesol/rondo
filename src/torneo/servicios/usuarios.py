"""Personas que usan la app (T6.2): crear con un rol y cambiar el rol.

La contraseña temporal se genera acá y se devuelve una sola vez, para mostrarla y entregarla
en persona. Solo se guarda su hash: nunca va a la base en claro ni al log.
"""

import secrets
import string

from django.contrib.auth.models import Group, User
from django.db import transaction

from torneo.permisos import MESA, ORGANIZACION

ROLES = {"organizacion": ORGANIZACION, "mesa": MESA}
# Sin letras ni números que se confundan al dictarla (O y 0, l y 1).
_ALFABETO = "".join(c for c in string.ascii_letters + string.digits if c not in "O0Il1")


def clave_temporal(largo: int = 12) -> str:
    return "".join(secrets.choice(_ALFABETO) for _ in range(largo))


@transaction.atomic
def crear_usuario(usuario: str, nombre: str, rol: str) -> tuple[User, str]:
    """Un usuario sin staff, con su grupo y una clave temporal (que se devuelve)."""
    clave = clave_temporal()
    nuevo = User(username=usuario.strip().lower(), first_name=nombre.strip())
    nuevo.set_password(clave)
    nuevo.save()
    nuevo.groups.add(Group.objects.get(name=ROLES[rol]))
    return nuevo, clave


@transaction.atomic
def cambiar_rol(usuario: User, rol: str) -> None:
    usuario.groups.remove(*Group.objects.filter(name__in=ROLES.values()))
    usuario.groups.add(Group.objects.get(name=ROLES[rol]))
