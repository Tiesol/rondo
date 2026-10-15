"""T13.1 (P68, P89): el escudo va por equipo del club. Paso 1 de 3: el modelo nuevo y el enlace
desde Equipo, todavía opcional."""

import django.db.models.deletion
import django.db.models.functions.text
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('torneo', '0033_planilla_flexible'),
    ]

    operations = [
        migrations.CreateModel(
            name='EquipoDeClub',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=80)),
                ('escudo', models.FileField(blank=True, max_length=200, upload_to='')),
                ('club', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='equipos_del_club', to='torneo.club')),
            ],
            options={
                'verbose_name': 'equipo del club',
                'verbose_name_plural': 'equipos del club',
                'ordering': ['club', 'nombre'],
                'constraints': [models.UniqueConstraint(models.F('club'), django.db.models.functions.text.Lower('nombre'), name='equipo_de_club_unico')],
            },
        ),
        migrations.AddField(
            model_name='equipo',
            name='equipo_de_club',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='equipos', to='torneo.equipodeclub'),
        ),
    ]
