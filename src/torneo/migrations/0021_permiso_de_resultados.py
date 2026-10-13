"""T8.5: la organización y la mesa cargan goles, tarjetas y resultados (P64)."""

from typing import Any

from django.apps.registry import Apps
from django.contrib.auth.management import create_permissions
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

GRUPOS = ("Organización", "Mesa de control")


def dar_permiso(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    configuracion: Any = apps.get_app_config("torneo")
    configuracion.models_module = True
    create_permissions(configuracion, apps=apps, verbosity=0)
    configuracion.models_module = None
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permiso = Permission.objects.get(content_type__app_label="torneo", codename="cargar_resultados")
    for grupo in Group.objects.filter(name__in=GRUPOS):
        grupo.permissions.add(permiso)


def sacar_permiso(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Permission = apps.get_model("auth", "Permission")
    Permission.objects.filter(content_type__app_label="torneo", codename="cargar_resultados").delete()


class Migration(migrations.Migration):
    dependencies = [("torneo", "0020_resultados")]

    operations = [migrations.RunPython(dar_permiso, sacar_permiso)]
