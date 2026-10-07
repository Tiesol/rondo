"""TU.2: grupos Organización y Mesa de control con sus permisos.

Los usuarios que ya existían sin grupo pasan a Organización: hasta acá, crear_usuario creaba
solo usuarios de la organización.
"""

from typing import Any

from django.apps.registry import Apps
from django.contrib.auth.management import create_permissions
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

# Copia fija de torneo.permisos.PERMISOS_POR_ROL: una migración no importa código que cambia.
PERMISOS_POR_ROL = {
    "Organización": [
        "configurar_torneo",
        "programar_partidos",
        "inscribir_equipos",
        "verificar_jugadores",
    ],
    "Mesa de control": ["inscribir_equipos", "verificar_jugadores"],
}


def crear_grupos(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    # Los permisos se crean después de migrar; acá hacen falta antes.
    configuracion: Any = apps.get_app_config("torneo")
    configuracion.models_module = True
    create_permissions(configuracion, apps=apps, verbosity=0)
    configuracion.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    User = apps.get_model("auth", "User")
    for nombre, codigos in PERMISOS_POR_ROL.items():
        grupo, _ = Group.objects.get_or_create(name=nombre)
        grupo.permissions.set(
            Permission.objects.filter(content_type__app_label="torneo", codename__in=codigos)
        )
    organizacion = Group.objects.get(name="Organización")
    for usuario in User.objects.filter(groups__isnull=True, is_superuser=False):
        usuario.groups.add(organizacion)


def borrar_grupos(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    apps.get_model("auth", "Group").objects.filter(name__in=PERMISOS_POR_ROL).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("torneo", "0004_permisos_de_los_roles"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [migrations.RunPython(crear_grupos, borrar_grupos)]
