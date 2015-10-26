# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('relocation', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='region',
            name='census_places',
            field=models.FilePathField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='region',
            name='dem',
            field=models.FilePathField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='region',
            name='floodplain_areas',
            field=models.FilePathField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='region',
            name='nlcd',
            field=models.FilePathField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='region',
            name='protected_areas',
            field=models.FilePathField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='region',
            name='slope',
            field=models.FilePathField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='region',
            name='tiger_lines',
            field=models.FilePathField(null=True, blank=True),
        ),
    ]
