# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('relocation', '0002_auto_20151026_1622'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='working_directory',
            field=models.FilePathField(allow_files=False, max_length=255, allow_folders=True, blank=True, path=b'C:\\Users\\dsx.AD3\\Code\\FloodMitigation\\locations', null=True),
        ),
        migrations.AlterField(
            model_name='location',
            name='boundary_polygon',
            field=models.FilePathField(allow_folders=True, max_length=255, allow_files=False, recursive=True),
        ),
        migrations.AlterField(
            model_name='location',
            name='search_area',
            field=models.FilePathField(max_length=255, path=b'C:\\Users\\dsx.AD3\\Code\\FloodMitigation\\locations', null=True, recursive=True, blank=True),
        ),
        migrations.AlterField(
            model_name='suitabilityanalysis',
            name='result',
            field=models.FilePathField(null=True, blank=True),
        ),
    ]
