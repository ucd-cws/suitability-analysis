from django.db import models
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.contrib import admin

# Create your models here.

import logging
import os
import shutil

# Get an instance of a logger
processing_log = logging.getLogger("processing_log")
geoprocessing_log = logging.getLogger("geoprocessing")

import arcpy

from code_library.common.geospatial import generate_gdb_filename

from relocation import gis
from relocation.gis import slope
from relocation.gis import protected_areas
from relocation.gis import merge
from relocation.gis import floodplain_areas
from relocation.gis import census_places
from relocation.gis import land_use

from FloodMitigation.settings import GEOSPATIAL_DIRECTORY, REGIONS_DIRECTORY, LOCATIONS_DIRECTORY

MERGE_CHOICES = (("INTERSECT", "INTERSECT"), ("ERASE", "ERASE"))


class InheritanceCastModel(models.Model):
	"""
	
	Model from http://stackoverflow.com/a/929982/587938 - used to obtain subclass object using parent class/relationship
	
	An abstract base class that provides a ``real_type`` FK to ContentType.

	For use in trees of inherited models, to be able to downcast
	parent instances to their child types.

	"""
	real_type = models.ForeignKey(ContentType, editable=False)

	def save(self, *args, **kwargs):
		if not self.id:
			self.real_type = self._get_real_type()
		super(InheritanceCastModel, self).save(*args, **kwargs)

	def _get_real_type(self):
		return ContentType.objects.get_for_model(type(self))

	def cast(self):
		return self.real_type.get_object_for_this_type(pk=self.pk)

	class Meta:
		abstract = True


class Region(models.Model):
	name = models.CharField(max_length=255, blank=False, null=False)
	short_name = models.SlugField(blank=False, null=False)
	crs_string = models.TextField(null=False, blank=False)

	base_directory = models.FilePathField(path=REGIONS_DIRECTORY, max_length=255, allow_folders=True, allow_files=False)
	layers = models.FilePathField(path=REGIONS_DIRECTORY, recursive=True, max_length=255, allow_folders=True, allow_files=False)

	# I was going to make it so all of these are required, but you could conceivably want to set up a region where
	# some of these aren't needed and they just aren't available. Available constraint validation should occur
	# when adding a constraint
	dem_name = models.CharField(max_length=255, )
	dem = models.FilePathField(null=True, blank=True)
	slope_name = models.CharField(max_length=255, )
	slope = models.FilePathField(null=True, blank=True)
	nlcd_name = models.CharField(max_length=255, )
	nlcd = models.FilePathField(null=True, blank=True)
	census_places_name = models.CharField(max_length=255, )
	census_places = models.FilePathField(null=True, blank=True)
	protected_areas_name = models.CharField(max_length=255, )
	protected_areas = models.FilePathField(null=True, blank=True)
	floodplain_areas_name = models.CharField(max_length=255, )
	floodplain_areas = models.FilePathField(null=True, blank=True)
	tiger_lines_name = models.CharField(max_length=255, )
	tiger_lines = models.FilePathField(null=True, blank=True)

	def setup(self):
		#if not (self.base_directory and self.layers):
		#	self.base_directory, self.layers = gis.create_working_directories(REGIONS_DIRECTORY, self.short_name)

		self.dem = os.path.join(str(self.layers), self.dem_name)
		self.slope = os.path.join(str(self.layers), self.slope_name)
		self.nlcd = os.path.join(str(self.layers), self.nlcd_name)
		self.census_places = os.path.join(str(self.layers), self.census_places_name)
		self.protected_areas = os.path.join(str(self.layers), self.protected_areas_name)
		self.floodplain_areas = os.path.join(str(self.layers), self.floodplain_areas_name)
		self.tiger_lines = os.path.join(str(self.layers), self.tiger_lines_name)
		self.save()

	def clean_working(self):
		pass
		# TODO: Make a function that cleans the layers that have been generated out, and resets the has_run and paths on the constraints

	def get_layer_names(self):
		"""
			gets a list of layer names to be our options when selecting layers for the region
		:return:
		"""
		original_workspace = arcpy.env.workspace

		arcpy.env.workspace = self.layers

		feature_classes = arcpy.ListFeatureClasses()
		rasters = arcpy.ListRasters()
		layers = feature_classes + rasters

		arcpy.env.workspace = original_workspace

		return layers

	def __str__(self):
		return unicode(self.name)

	def __unicode__(self):
		return unicode(self.name)
		
		
class RegionForm(forms.ModelForm):
	dem_name = forms.ChoiceField()
	slope_name = forms.ChoiceField()
	nlcd_name = forms.ChoiceField()
	census_places_name = forms.ChoiceField()
	protected_areas_name = forms.ChoiceField()
	floodplain_areas_name = forms.ChoiceField()
	tiger_lines_name = forms.ChoiceField()

	def __init__(self, *args, **kwargs):
		super(SuitabilityAnalysisForm, self).__init__(*args, **kwargs)
		self.fields['dem'].choices = self.instance.get_layer_names()
		self.fields['slope'].choices = self.fields['dem'].choices
		self.fields['nlcd'].choices = self.fields['dem'].choices
		self.fields['census_places'].choices = self.fields['dem'].choices
		self.fields['protected_areas'].choices = self.fields['dem'].choices
		self.fields['floodplain_areas'].choices = self.fields['dem'].choices
		self.fields['tiger_lines'].choices = self.fields['dem'].choices

	class Meta:
		model = Region
		exclude = []
		
class RegionAdmin(admin.ModelAdmin):
	form = RegionForm
	

class Location(models.Model):
	name = models.CharField(max_length=255)
	short_name = models.SlugField(blank=False, null=False)
	region = models.ForeignKey(Region, null=False)

	working_directory = models.FilePathField(path=LOCATIONS_DIRECTORY, max_length=255, allow_folders=True, allow_files=False, null=True, blank=True)
	layers = models.FilePathField(path=LOCATIONS_DIRECTORY, recursive=True, max_length=255, allow_folders=True, allow_files=False)

	boundary_polygon_name = models.CharField(max_length=255)
	boundary_polygon = models.FilePathField(null=True, blank=True, recursive=True, max_length=255, allow_folders=True, allow_files=False)

	search_distance = models.IntegerField(default=25000)  # meters
	search_area = models.FilePathField(path=LOCATIONS_DIRECTORY, recursive=True, max_length=255, allow_folders=False, allow_files=True, null=True, blank=True)  # storage for boundary_polygon buffered by search_distance

	def setup(self):
		"""
			setup must be run first on Suitability Analysis object!
		"""

		self.boundary_polygon = os.path.join(str(self.layers), self.boundary_polygon_name)

		if self.search_area is None or self.search_area == "":
			self.search_area = generate_gdb_filename("search_area", gdb=self.suitability_analysis.workspace)
			geoprocessing_log.info("Running buffer or area boundary to find search area")
			arcpy.Buffer_analysis(self.boundary_polygon, self.search_area, self.search_distance)

		self.save()

	def __str__(self):
		return unicode(self.name)

	def __unicode__(self):
		return unicode(self.name)


class SuitabilityAnalysis(models.Model):
	name = models.CharField(max_length=255, blank=False, null=False)
	short_name = models.SlugField(blank=False, null=False)

	location = models.OneToOneField(Location, related_name="suitability_analysis")
	result = models.FilePathField(null=True, blank=True)

	working_directory = models.FilePathField(path=GEOSPATIAL_DIRECTORY, max_length=255, allow_folders=True, allow_files=False, null=True, blank=True)
	workspace = models.FilePathField(path=GEOSPATIAL_DIRECTORY, recursive=True, max_length=255, allow_folders=True, allow_files=False, null=True, blank=True)

	def setup(self):
		self.working_directory, self.workspace = gis.create_working_directories(GEOSPATIAL_DIRECTORY, self.location.region.short_name)
		self.save()

	def merge(self):
		suitable_areas = self.location.search_area
		for constraint in self.constraints.all():
			full_constraint = constraint.cast()  # get the subobject
			
			if not full_constraint.enabled:
				continue
			if not full_constraint.has_run:  # basically, is the constraint ready to merge? We need to preprocess some of them
				full_constraint.run()  # run constraint

			suitable_areas = merge.merge(suitable_areas, full_constraint.polygon_layer, self.workspace, full_constraint.merge_type)

		self.result = suitable_areas
		self.save()

	def __str__(self):
		return unicode(self.name)

	def __unicode__(self):
		return unicode(self.name)
	
	
class Constraint(InheritanceCastModel):
	"""

	"""
	enabled = models.BooleanField(default=True)
	name = models.CharField(max_length=31)
	description = models.TextField()

	polygon_layer = models.FilePathField(null=True, blank=True)
	has_run = models.BooleanField(default=False)

	suitability_analysis = models.ForeignKey(SuitabilityAnalysis, related_name="constraints")

	def rerun(self):
		"""
			Force it to run again
		"""
		self.has_run = False
		self.run()
	
	def __str__(self):
		return unicode(self.name)

	def __unicode__(self):
		return unicode(self.name)

class LocalSlopeConstraint(Constraint):
	merge_type = models.CharField(default="INTERSECT", choices=MERGE_CHOICES, max_length=255)  # it comes out with places of acceptable slope
	max_slope = models.IntegerField(default=30)

	def run(self):
		processing_log.info("Running Local Slope Constraint")
		self.polygon_layer = slope.process_local_slope(slope=self.suitability_analysis.location.region.slope,
														max_slope=30,
														mask=self.suitability_analysis.location.search_area,
														return_type="polygon", workspace=self.suitability_analysis.workspace)

		self.has_run = True
		self.save()


class ProtectedAreasConstraint(Constraint):
	merge_type = models.CharField(default="ERASE", choices=MERGE_CHOICES, max_length=255)

	def run(self):
		processing_log.info("Running Protected Areas Constraint")
		self.polygon_layer = protected_areas.protected_areas(self.suitability_analysis.location.region.protected_areas)

		self.has_run = True
		self.save()


class LandUseConstraint(Constraint):
	merge_type = models.CharField(default="ERASE", choices=MERGE_CHOICES, max_length=255)

	def run(self):
		processing_log.info("Running Land Use Constraint")
		self.polygon_layer = land_use.land_use(self.suitability_analysis.location.region.nlcd,
													self.suitability_analysis.location.search_area,
													self.suitability_analysis.location.region.tiger_lines,
													self.suitability_analysis.location.region.census_places,
													self.suitability_analysis.location.region.crs_string,
													self.suitability_analysis.workspace)

		self.has_run = True
		self.save()


class FloodplainAreasConstraint(Constraint):
	merge_type = models.CharField(default="ERASE", choices=MERGE_CHOICES, max_length=255)

	def run(self):
		processing_log.info("Running Floodplain Areas Constraint")
		self.polygon_layer = floodplain_areas.floodplain_areas(self.suitability_analysis.location.region.floodplain_areas)

		self.has_run = True
		self.save()


class CensusPlacesConstraint(Constraint):
	merge_type = models.CharField(default="ERASE", choices=MERGE_CHOICES, max_length=255)

	def run(self):
		processing_log.info("Running Floodplain Areas Constraint")
		self.polygon_layer = census_places.census_places(self.suitability_analysis.location.region.floodplain_areas)

		self.has_run = True
		self.save()
