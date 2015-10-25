from django.db import models

# Create your models here.

import logging
import os
import shutil

# Get an instance of a logger
processing_log = logging.getLogger("processing_log")

import arcpy

from code_library.common.geospatial import generate_gdb_filename

from relocation import gis
from relocation.gis import slope
from relocation.gis import protected_areas
from relocation.gis import merge

from FloodMitigation.settings import GEOSPATIAL_DIRECTORY, REGIONS_DIRECTORY

MERGE_CHOICES = (("IN", "INTERSECT"), ("ER", "ERASE"))


class Region(models.Model):
	name = models.CharField(max_length=255)
	short_name = models.CharField(unique=True, max_length=255)

	base_directory = models.FilePathField()
	layers = models.FilePathField()

	dem = models.FilePathField()
	slope = models.FilePathField()
	census_places = models.FilePathField()

	def setup(self):
		self.base_directory, self.layers = gis.create_working_directories(REGIONS_DIRECTORY, self.short_name)
		self.save()

class Location(models.Model):
	name = models.CharField(max_length=255)
	boundary_polygon = models.FilePathField()
	search_distance = models.IntegerField(default=25000)  # meters
	search_area = models.FilePathField()  # storage for boundary_polygon buffered by search_distance


class Constraint(models.Model):
	"""

	"""
	enabled = models.BooleanField(default=True)
	name = models.CharField(max_length=31)
	description = models.TextField()
	has_run = models.BooleanField(default=False)

	def run(self, workspace):
		self.has_run = True
		self.save()


class SlopeConstraint(Constraint):
	function = slope.process_local_slope
	merge_type = models.CharField(default="ERASE", choices=MERGE_CHOICES, max_length=255)


class SuitabilityAnalysis(models.Model):
	location = models.ForeignKey(Location)
	constraints = models.ManyToManyField(Constraint)
	result = models.FilePathField()

	working_directory = models.FilePathField()
	workspace = models.FilePathField()

	def setup(self):
		self.working_directory, self.workspace = gis.create_working_directories(GEOSPATIAL_DIRECTORY, self.location.region.short_name)
		self.save()

	def merge(self):
		suitable_areas = self.location.search_area
		for constraint in self.constraints.all():
			if not constraint.has_run:  # basically, is the constraint ready to merge? We need to preprocess some of them
				constraint.run(workspace=self.workspace)  # run constraint

			suitable_areas = merge.merge(suitable_areas, constraint.layer, self.workspace, constraint.merge_type)
