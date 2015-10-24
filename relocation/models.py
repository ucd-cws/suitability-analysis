from django.db import models

# Create your models here.

import logging
import os
import shutil

# Get an instance of a logger
processing_log = logging.getLogger("processing_log")

import arcpy

from code_library.common.geospatial import generate_gdb_filename

from relocation.gis import slope
from relocation.gis import protected_areas
from relocation.gis import merge

from FloodMitigation.settings import GEOSPATIAL_DIRECTORY

MERGE_CHOICES = ("INTERSECT", "ERASE")


class Region(models.Model):
	name = models.CharField()
	short_name = models.CharField(unique=True)
	dem = models.FileField()
	slope = models.FileField()


class Location(models.Model):
	name = models.CharField()
	boundary_polygon = models.FilePathField()
	search_distance = models.IntegerField(default=25000)  # meters
	search_area = models.FilePathField()  # storage for boundary_polygon buffered by search_distance


class Constraint(models.Model):
	"""

	"""
	enabled = models.BooleanField(default=True)
	name = models.TextField(max_length=255)
	description = models.TextField()
	has_run = models.BooleanField(default=False)

	merge_type = models.CharField(choices=MERGE_CHOICES)

	def run(self, workspace):


		self.has_run = True
		self.save()


class SlopeConstraint(Constraint):
	function = slope.process_local_slope
	merge_type = models.CharField(default="ERASE", choices=MERGE_CHOICES)


class SuitabilityAnalysis(models.Model):
	location = models.ForeignKey(Location)
	constraints = models.ManyToManyField(Constraint)
	result = models.FileField()

	working_directory = models.FilePathField()
	workspace = models.FilePathField()

	def setup(self):

		gdb_name = "layers.gdb"
		folder_name = self.location.region.short_name
		self.working_directory = os.path.join(GEOSPATIAL_DIRECTORY, folder_name)

		if os.path.exists(self.working_directory):
			processing_log.warning("processing directory for project already exists - deleting!")
			shutil.rmtree(self.working_directory)

		os.mkdir(self.working_directory)
		arcpy.CreateFileGDB_management(self.working_directory, gdb_name)
		self.workspace = os.path.join(self.working_directory, gdb_name)

		self.save()

	def merge(self):
		suitable_areas = self.location.search_area
		for constraint in self.constraints.all():
			if not constraint.has_run:
				constraint.run(workspace=self.workspace)  # run constraint

			suitable_areas = merge.merge(suitable_areas, constraint.layer, self.workspace, constraint.merge_type)
