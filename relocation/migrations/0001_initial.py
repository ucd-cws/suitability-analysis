# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Constraint',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('enabled', models.BooleanField(default=True)),
                ('name', models.CharField(max_length=31)),
                ('description', models.TextField()),
                ('polygon_layer', models.FilePathField()),
                ('has_run', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('short_name', models.SlugField()),
                ('boundary_polygon', models.FilePathField()),
                ('search_distance', models.IntegerField(default=25000)),
                ('search_area', models.FilePathField()),
            ],
        ),
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('short_name', models.SlugField()),
                ('crs_string', models.TextField()),
                ('base_directory', models.FilePathField(path=b'C:\\Users\\dsx.AD3\\Code\\FloodMitigation\\regions', max_length=255, allow_files=False, allow_folders=True)),
                ('layers', models.FilePathField(path=b'C:\\Users\\dsx.AD3\\Code\\FloodMitigation\\regions', max_length=255, allow_files=False, recursive=True, allow_folders=True)),
                ('dem_name', models.CharField(max_length=255)),
                ('dem', models.FilePathField()),
                ('slope_name', models.CharField(max_length=255)),
                ('slope', models.FilePathField()),
                ('nlcd_name', models.CharField(max_length=255)),
                ('nlcd', models.FilePathField()),
                ('census_places_name', models.CharField(max_length=255)),
                ('census_places', models.FilePathField()),
                ('protected_areas_name', models.CharField(max_length=255)),
                ('protected_areas', models.FilePathField()),
                ('floodplain_areas_name', models.CharField(max_length=255)),
                ('floodplain_areas', models.FilePathField()),
                ('tiger_lines_name', models.CharField(max_length=255)),
                ('tiger_lines', models.FilePathField()),
            ],
        ),
        migrations.CreateModel(
            name='SuitabilityAnalysis',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('short_name', models.SlugField()),
                ('result', models.FilePathField()),
                ('working_directory', models.FilePathField(path=b'C:\\Users\\dsx.AD3\\Code\\FloodMitigation\\geospatial_analysis', max_length=255, allow_files=False, allow_folders=True)),
                ('workspace', models.FilePathField(path=b'C:\\Users\\dsx.AD3\\Code\\FloodMitigation\\geospatial_analysis', max_length=255, allow_files=False, recursive=True, allow_folders=True)),
            ],
        ),
        migrations.CreateModel(
            name='CensusPlacesConstraint',
            fields=[
                ('constraint_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='relocation.Constraint')),
                ('merge_type', models.CharField(default=b'ERASE', max_length=255, choices=[(b'IN', b'INTERSECT'), (b'ER', b'ERASE')])),
            ],
            bases=('relocation.constraint',),
        ),
        migrations.CreateModel(
            name='FloodplainAreasConstraint',
            fields=[
                ('constraint_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='relocation.Constraint')),
                ('merge_type', models.CharField(default=b'ERASE', max_length=255, choices=[(b'IN', b'INTERSECT'), (b'ER', b'ERASE')])),
            ],
            bases=('relocation.constraint',),
        ),
        migrations.CreateModel(
            name='LandUseConstraint',
            fields=[
                ('constraint_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='relocation.Constraint')),
                ('merge_type', models.CharField(default=b'ERASE', max_length=255, choices=[(b'IN', b'INTERSECT'), (b'ER', b'ERASE')])),
            ],
            bases=('relocation.constraint',),
        ),
        migrations.CreateModel(
            name='LocalSlopeConstraint',
            fields=[
                ('constraint_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='relocation.Constraint')),
                ('merge_type', models.CharField(default=b'ERASE', max_length=255, choices=[(b'IN', b'INTERSECT'), (b'ER', b'ERASE')])),
                ('max_slope', models.IntegerField(default=30)),
            ],
            bases=('relocation.constraint',),
        ),
        migrations.CreateModel(
            name='ProtectedAreasConstraint',
            fields=[
                ('constraint_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='relocation.Constraint')),
                ('merge_type', models.CharField(default=b'ERASE', max_length=255, choices=[(b'IN', b'INTERSECT'), (b'ER', b'ERASE')])),
            ],
            bases=('relocation.constraint',),
        ),
        migrations.AddField(
            model_name='suitabilityanalysis',
            name='constraints',
            field=models.ManyToManyField(related_name='suitability_analysis', to='relocation.Constraint'),
        ),
        migrations.AddField(
            model_name='suitabilityanalysis',
            name='location',
            field=models.ForeignKey(related_name='suitability_analysis', to='relocation.Location'),
        ),
        migrations.AddField(
            model_name='location',
            name='region',
            field=models.ForeignKey(to='relocation.Region'),
        ),
    ]
