from django.db import models

# Create your models here.

import arcpy

from relocation.gis import slope
from relocation.gis import protected_areas
from relocation.gis import merge

MERGE_CHOICES = ("INTERSECT", "ERASE")


class Region(models.Model):
	name = models.CharField()
	dem = models.FileField()
	slope = models.FileField()


class Location(models.Model):
	name = models.CharField()
	boundary_polygon = models.FileField()
	search_distance = models.IntegerField(default=25000)  # meters
	search_area = models.FileField()  # storage for boundary_polygon buffered by search_distance


class Constraint(models.Model):
	"""

	"""
	enabled = models.BooleanField(default=True)
	name = models.TextField(max_length=255)
	description = models.TextField()
	has_run = models.BooleanField(default=False)

	merge_type = models.CharField(choices=MERGE_CHOICES)github

	def run(self):
		pass


class SlopeConstraint(Constraint):
	function = slope.process_local_slope
	merge_type = models.CharField(default="ERASE", choices=MERGE_CHOICES)


class Suitability(models.Model):
	location = models.ForeignKey(Location)
	constraints = models.ManyToManyField(Constraint)
	result = models.FileField()
	workspace = models.FilePathField()

	def merge(self):
		suitable_areas = self.location.search_area
		for constraint in self.constraints.all():
			if not constraint.has_run:
				constraint.run(workspace=self.workspace)  # run constraint

			suitable_areas = merge.merge(suitable_areas, constraint.layer, self.workspace, constraint.merge_type)

			pass