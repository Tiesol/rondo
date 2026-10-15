"""T13.1, paso 3 de 3: el enlace pasa a ser obligatorio, la unicidad es (equipo del club,
categoría) y el club ya no tiene escudo (se copió en el paso 2)."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('torneo', '0035_copiar_escudos'),
    ]

    operations = [
        migrations.AlterField(
            model_name='equipo',
            name='equipo_de_club',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='equipos', to='torneo.equipodeclub'),
        ),
        migrations.RemoveConstraint(
            model_name='equipo',
            name='equipo_unico_por_club_y_categoria',
        ),
        migrations.AddConstraint(
            model_name='equipo',
            constraint=models.UniqueConstraint(fields=('equipo_de_club', 'categoria'), name='equipo_unico_por_categoria', violation_error_message='Ya hay un equipo con ese nombre, de ese club, en esa categoría.'),
        ),
        migrations.RemoveField(
            model_name='club',
            name='escudo',
        ),
    ]
