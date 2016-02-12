from django.db import models
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.contrib import admin

# Create your models here.

import six
import sys
import logging
import os
import shutil
import traceback

# Get an instance of a logger
processing_log = logging.getLogger("processing_log")
geoprocessing_log = logging.getLogger("geoprocessing")

import arcpy

from FloodMitigation.settings import DEBUG

from relocation.gis.temp import generate_gdb_filename

from relocation import gis
from relocation.gis import slope
from relocation.gis import protected_areas
from relocation.gis import merge
from relocation.gis import floodplain_areas
from relocation.gis import census_places
from relocation.gis import land_use
from relocation.gis import roads
from relocation.gis import geometry
from relocation.gis import geojson
from relocation.gis import parcels

from FloodMitigation.settings import BASE_DIR, GEOSPATIAL_DIRECTORY, REGIONS_DIRECTORY, LOCATIONS_DIRECTORY

MERGE_CHOICES = (("INTERSECT", "INTERSECT"), ("ERASE", "ERASE"), ("UNION", "UNION"), ("RASTER_ADD", "RASTER_ADD"))
LAND_COVER_CHOICES = (
	(11, "11 - Open Water"),
	(12, "12 - Perennial Ice/Snow"),
	(21, "21 - Developed, Open Space"),
	(22, "22 - Developed, Low Intensity"),
	(23, "23 - Developed, Medium Intensity "),
	(24, "24 - Developed, High Intensity "),
	(31, "31 - Barren Land (Rock/Sand/Clay)"),
	(41, "41 - Deciduous Forest"),
	(42, "42 - Evergreen Forest"),
	(43, "43 - Mixed Forest"),
	(51, "51 - Dwarf Scrub"),
	(52, "52 - Shrub/Scrub"),
	(71, "71 - Grassland/Herbaceous"),
	(72, "72 - Sedge/Herbaceous"),
	(73, "73 - Lichens"),
	(74, "74 - Moss"),
	(81, "81 - Pasture/Hay"),
	(82, "82 - Cultivated Crops"),
	(90, "90 - Woody Wetlands"),
	(95, "95 - Emergent Herbaceous Wetlands ")
)


class InheritanceCastModel(models.Model):
	"""
	
	Model from http://stackoverflow.com/a/929982/587938 - used to obtain subclass object using parent class/relationship
	
	An abstract base class that provides a ``real_type`` ForeignKey to ContentType.

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
	derived_layers = models.FilePathField(path=REGIONS_DIRECTORY, recursive=True, max_length=255, allow_folders=True, allow_files=False, null=True, blank=True)

	# I was going to make it so all of these are required, but you could conceivably want to set up a region where
	# some of these aren't needed and they just aren't available. Available constraint validation should occur
	# when adding a constraint
	dem_name = models.CharField(max_length=255, )
	dem = models.FilePathField(null=True, blank=True, editable=False)
	slope_name = models.CharField(max_length=255, )
	slope = models.FilePathField(null=True, blank=True, editable=False)
	nlcd_name = models.CharField(max_length=255, )
	nlcd = models.FilePathField(null=True, blank=True, editable=False)
	census_places_name = models.CharField(max_length=255, )
	census_places = models.FilePathField(null=True, blank=True, editable=False)
	protected_areas_name = models.CharField(max_length=255, )
	protected_areas = models.FilePathField(null=True, blank=True, editable=False)
	floodplain_areas_name = models.CharField(max_length=255, )
	floodplain_areas = models.FilePathField(null=True, blank=True, editable=False)
	tiger_lines_name = models.CharField(max_length=255, )
	tiger_lines = models.FilePathField(null=True, blank=True, editable=False)
	parcels_name = models.CharField(max_length=255, null=True, blank=True)
	parcels = models.FilePathField(null=True, blank=True, editable=False)
	floodplain_distance = models.FilePathField(null=True, blank=True, editable=True)

	def setup(self, do_all=True):
		#if not (self.base_directory and self.layers):
		#	self.base_directory, self.layers = gis.create_working_directories(REGIONS_DIRECTORY, self.short_name)

		self.dem = os.path.join(str(self.layers), self.dem_name)
		self.slope = os.path.join(str(self.layers), self.slope_name)
		self.nlcd = os.path.join(str(self.layers), self.nlcd_name)
		self.census_places = os.path.join(str(self.layers), self.census_places_name)
		self.protected_areas = os.path.join(str(self.layers), self.protected_areas_name)
		self.floodplain_areas = os.path.join(str(self.layers), self.floodplain_areas_name)
		self.tiger_lines = os.path.join(str(self.layers), self.tiger_lines_name)
		self.parcels = os.path.join(str(self.layers), self.parcels_name)
		self.save()

		if do_all:
			self.process_derived()

	def process_derived(self):
		"""
			Processes any necessary derived layers that should be precomputed based on input layers
		:return:
		"""
		if not self.derived_layers:
			derived_name = "derived.gdb"
			if not os.path.exists(os.path.join(self.base_directory, derived_name)):
				arcpy.CreateFileGDB_management(self.base_directory, derived_name)

			self.derived_layers = os.path.join(self.base_directory, derived_name)
			self.save()

		self.compute_floodplain_distance()

		self.save()

	def compute_floodplain_distance(self, cell_size=30):

		arcpy.CheckOutExtension("Spatial")
		stored_environments = gis.store_environments(["mask", "extent"])  # back up the existing settings for environment variables
		arcpy.env.mask = self.dem  # set the analysis to only occur as large as the parcels layer
		arcpy.env.extent = self.dem

		geoprocessing_log.info("Computing Floodplain Distance")

		distance_raster = generate_gdb_filename("floodplain_distance_raster", gdb=self.derived_layers)
		distance_raster_unsaved = arcpy.sa.EucDistance(self.floodplain_areas, cell_size=cell_size)
		distance_raster_unsaved.save(distance_raster)

		gis.reset_environments(stored_environments=stored_environments)  # restore the environment variable settings to original values
		arcpy.CheckInExtension("Spatial")

		self.floodplain_distance = distance_raster
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
		return six.b(self.name)

	def __unicode__(self):
		return six.u(self.name)
		
		
class RegionForm(forms.ModelForm):
	dem_name = forms.ChoiceField()
	slope_name = forms.ChoiceField()
	nlcd_name = forms.ChoiceField()
	census_places_name = forms.ChoiceField()
	protected_areas_name = forms.ChoiceField()
	floodplain_areas_name = forms.ChoiceField()
	tiger_lines_name = forms.ChoiceField()

	def __init__(self, *args, **kwargs):
		super(RegionForm, self).__init__(*args, **kwargs)
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
	boundary_polygon = models.FilePathField(null=True, blank=True, recursive=True, max_length=255, allow_folders=True, allow_files=False, editable=False)

	search_distance = models.IntegerField(default=25000)  # meters
	search_area = models.FilePathField(path=LOCATIONS_DIRECTORY, recursive=True, max_length=255, allow_folders=False, allow_files=True, null=True, blank=True, editable=False)  # storage for boundary_polygon buffered by search_distance

	def setup(self):
		"""
			setup must be run first on Suitability Analysis object!
		"""

		self.boundary_polygon = os.path.join(str(self.layers), self.boundary_polygon_name)

		if self.search_area is None or self.search_area == "":
			self.search_area = generate_gdb_filename("search_area", gdb=self.suitability_analysis.workspace)
			geoprocessing_log.info("Running buffer or area boundary to find search area")
			arcpy.Buffer_analysis(self.boundary_polygon, self.search_area, self.search_distance)

		if self.parcels.layer is None or self.parcels.layer == "":
			self.parcels.layer = generate_gdb_filename(self.region.parcels_name, gdb=self.layers)
			geoprocessing_log.info("Copying parcels layer to location geodatabase")
			arcpy.CopyFeatures_management(self.region.parcels, self.parcels.layer)
			self.parcels.save()

		self.save()

	def __str__(self):
		return six.b(self.name)

	def __unicode__(self):
		return six.u(self.name)


class Parcels(models.Model):
	"""
		A place to aggregate functions that operate on parcels
	"""

	layer = models.FilePathField(null=True, blank=True, editable=True)
	original_layer = models.FilePathField(null=True, blank=True, editable=True)
	id_field = models.CharField(max_length=255, default="OBJECTID", null=True, blank=True)

	def setup(self):
		self.duplicate_layer()  # copy the parcels out so that we can keep a fresh copy for reprocessing still
		self.compute_distance_to_floodplain()
		self.compute_centroid_elevation()
		self.compute_slopes()
		self.compute_centroid_distances()
		self.save()

		self.as_geojson()  # once processing is complete, export the geojson version so it's up to date.

	def duplicate_layer(self):
		"""
			Duplicates the parcels layer into the suitability analysis so we always have the original copy
		:return:
		"""

		new_name = arcpy.CreateUniqueName(os.path.split(self.original_layer)[1], self.suitability_analysis.workspace)  # get me a new name in the same geodatabase
		new_path = os.path.join(self.suitability_analysis.workspace, new_name)
		arcpy.CopyFeatures_management(self.original_layer, new_path)
		self.layer = new_path
		self.save()

	def get_join_field(self):
		"""
			A special case occurs if the id_field is OBJECTID because ArcGIS renames the field to OBJECTID_1
			This function provides that as a join field when applicable, and returns the original field otherwise
		:return:
		"""
		if self.id_field == "OBJECTID":
			return "OBJECTID_1"
		else:
			return self.id_field

	def zonal_min_max_mean(self, raster, name):
		"""
			Extracts zonal statistics from a raster, and joins the min, max, and mean back to the parcels layer.
			Given a raster and a name, fields will be named mean_{name}, min_{name}, and max_{name}
		:param raster: An ArcGIS-compatible raster path
		:param name: The name to suffix fields with
		:return:
		"""
		self.check_values()

		arcpy.CheckOutExtension("Spatial")

		geoprocessing_log.info("Running Zonal Statistics for {0:s}".format(name))
		zonal_table = generate_gdb_filename(name_base="zonal_table", scratch=True)
		arcpy.sa.ZonalStatisticsAsTable(self.layer, self.id_field, raster, zonal_table, statistics_type="MIN_MAX_MEAN")

		join_field = self.get_join_field()
		try:
			geoprocessing_log.info("Joining {0:s} Zone Statistics to Parcels".format(name))
			gis.permanent_join(self.layer, self.id_field, zonal_table, join_field, "MEAN", rename_attribute="mean_{0:s}".format(name))
			gis.permanent_join(self.layer, self.id_field, zonal_table, join_field, "MIN", rename_attribute="min_{0:s}".format(name))
			gis.permanent_join(self.layer, self.id_field, zonal_table, join_field, "MAX", rename_attribute="max_{0:s}".format(name))
		except:
			if not DEBUG:
				geoprocessing_log.error("Unable to join zonal {0:s} back to parcels".format(name))
			else:
				six.reraise(*sys.exc_info())

		arcpy.CheckInExtension("Spatial")

	def check_values(self):
		"""
			Just a way to check that we're ready to go since these fields aren't required initially.
		:return:
		"""
		if not self.layer:
			raise ValueError("Parcel layer (attribute: layer) is not defined - can't proceed with computations!")

		if not self.id_field:
			raise ValueError("Parcel ID/ObjectID field (attribute: id_field) is not defined - can't proceed with computations!")

	def compute_slopes(self):
		self.zonal_min_max_mean(self.suitability_analysis.location.region.dem, "elevation")
		self.zonal_min_max_mean(self.suitability_analysis.location.region.slope, "slope")

	def compute_centroid_elevation(self):

		self.check_values()
		arcpy.CheckOutExtension("Spatial")
		new_field_name = "centroid_elevation"

		processing_log.info("Computing Centroid Elevation")
		centroids = geometry.get_centroids(self.layer, as_file=True, id_field=self.id_field)
		elevation_points = generate_gdb_filename("elevation_points", scratch=True)
		arcpy.sa.ExtractValuesToPoints(centroids, self.suitability_analysis.location.region.dem, elevation_points)

		try:
			processing_log.info("Permanent Join")
			gis.permanent_join(self.layer, self.id_field, elevation_points, "ORIG_FID", "RASTERVALU", new_field_name)
		except:
			if not DEBUG:
				processing_log.error("Error attaching centroid elevation information - this information is currently missing from the parcels - correct your inputs or the code and reprocess the parcels, or this metric will be unavailable")
			else:
				six.reraise(*sys.exc_info())

		arcpy.CheckInExtension("Spatial")

	def compute_centroid_distances(self):
		new_field_name = "centroid_distance_to_original_boundary"

		self.check_values()

		processing_log.info("Centroid Near Distance")
		distance_information = gis.centroid_near_distance(self.layer, self.suitability_analysis.location.boundary_polygon, self.id_field, self.suitability_analysis.location.search_distance)
		try:
			processing_log.info("Permanent Join")
			gis.permanent_join(self.layer, self.id_field, distance_information["table"], "INPUT_FID", "DISTANCE", new_field_name)  # INPUT_FID and DISTANCE are results of ArcGIS, so it's safe *enough* to hard-code them.
		except:  # just trying to keep the whole program coming down if an exception is raised during processing
			if not DEBUG:
				processing_log.error("Error attaching centroid distance information - this information is currently missing from the parcels - correct your inputs or the code and reprocess the centroid distnances, or this metric will be unavailable")
			else:
				six.reraise(*sys.exc_info())

	def compute_distance_to_floodplain(self):

		self.check_values()

		processing_log.info("Getting Distance To Floodplain")

		self.zonal_min_max_mean(self.suitability_analysis.location.region.floodplain_distance, "distance_to_floodplain")

	def as_geojson(self):
		geodatabase, layer_name = os.path.split(self.layer)
		try:
			geojson_folder = os.path.join(BASE_DIR, "relocation", "static", "relocation", "geojson", "parcels")
			if not os.path.exists(geojson_folder):  # if the folder doesn't already exist
				os.makedirs(geojson_folder)  # make it

			output_file = os.path.join(geojson_folder, "{0:s}.geojson".format(self.id))  # set the full name of the output file
			geojson.file_gdb_layer_to_geojson(geodatabase, layer_name, output_file)  # run the convert
		except:
			geoprocessing_log.error("Unable to convert parcels layer to geojson")


class SuitabilityAnalysis(models.Model):
	name = models.CharField(max_length=255, blank=False, null=False)
	short_name = models.SlugField(blank=False, null=False)

	location = models.OneToOneField(Location, related_name="suitability_analysis")
	result = models.FilePathField(null=True, blank=True)
	potential_suitable_areas = models.FilePathField(null=True, blank=True)
	split_potential_areas = models.FilePathField(null=True, blank=True)

	working_directory = models.FilePathField(path=GEOSPATIAL_DIRECTORY, max_length=255, allow_folders=True, allow_files=False, null=True, blank=True)
	workspace = models.FilePathField(path=GEOSPATIAL_DIRECTORY, recursive=True, max_length=255, allow_folders=True, allow_files=False, null=True, blank=True)

	# parcels layer will be copied over from the Region, but then work will proceed on it here so the region remains pure but the location starts modifying it for its own parameters
	parcels = models.OneToOneField(Parcels, related_name="suitability_analysis")

	def setup(self):
		self.working_directory = gis.create_working_directories(GEOSPATIAL_DIRECTORY, self.location.region.short_name)
		self.workspace = arcpy.CreateFileGDB_management(self.working_directory, "{0:s}_layers.gdb".format(self.short_name))

		self.parcels = Parcels()  # pass in the parcels layer for setup
		self.parcels.original_layer = self.location.region.parcels
		self.parcels.save()
		self.save()

	def merge(self):
		self.potential_suitable_areas = merge.merge_constraints(self.location.search_area, self.constraints.all(), self.workspace)
		self.split_potential_areas = self.split()

		self.result = self.potential_suitable_areas
		self.save()

		return self.result

	def __str__(self):
		return self.name

	def __unicode__(self):
		return six.u(self.name)

	def generate_mesh(self):
		"""
			TODO: Placeholder function - implement the hexagonal mesh. Need to move on and use the parcels for now)
		:return: path to feature class of the new mesh, in the location gdb
		"""

		return self.location.region.parcels

	def split(self):
		"""
			After the initial merge is done, this method splits up the potential areas based on the parcels (or hexagonal data)
		:return:
		"""

		if not self.potential_suitable_areas:
			processing_log.error("potential_suitable_areas is not defined - the split method can only be called after a merge has initiated, generated, and saved the potential suitable areas")
			raise ValueError("potential_suitable_areas is not defined - the split method can only be called after a merge has initiated, generated, and saved the potential suitable areas")

		if self.location.region.parcels:
			mesh = self.location.region.parcels
		else:
			mesh = self.generate_mesh()

		split_areas = generate_gdb_filename(gdb=self.workspace)
		geoprocessing_log.info("Intersecting potential areas with parcels")
		arcpy.Intersect_analysis(in_features=[self.potential_suitable_areas, self.mesh], out_feature_class=split_areas)

		return split_areas


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
		return six.b(self.name)

	def __unicode__(self):
		return six.u(self.name)


class UnionConstraint(Constraint):
	"""
		We may ultimately want to abstract this into a nested constraint generally, but for now, Unioning is one of the only reasons to do this.
		Provides a constraint grouping that can be unioned before then being intersected or erasing
	"""

	# merge_type = models.CharField(default="INTERSECT", choices=MERGE_CHOICES, max_length=20)
	# constraints = Constraints relationship defined by the subobjects as a foreign key

	def run(self):
		self.polygon_layer = merge.merge_constraints(self.location.search_area, self.constraints.all(), self.workspace)

	class Meta:
		abstract = True


class LocalSlopeConstraint(Constraint):
	merge_type = models.CharField(default="INTERSECT", choices=MERGE_CHOICES, max_length=255)  # it comes out with places of acceptable slope
	max_slope = models.IntegerField(default=5)

	def run(self):
		processing_log.info("Running Local Slope Constraint")
		self.polygon_layer = slope.process_local_slope(slope=self.suitability_analysis.location.region.slope,
														max_slope=self.max_slope,
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


class LandCoverChoice(models.Model):
	value = models.IntegerField(choices=LAND_COVER_CHOICES, unique=True)

	def __str__(self):
		return six.b(self.value)

	def __unicode__(self):
		return six.u(self.value)


class LandCoverConstraint(Constraint):
	merge_type = models.CharField(default="ERASE", choices=MERGE_CHOICES, max_length=255)
	excluded_types = models.ManyToManyField(LandCoverChoice)

	def run(self):
		processing_log.info("Running Land Use Constraint")
		self.polygon_layer = land_use.land_use(self.suitability_analysis.location.region.nlcd,
													self.suitability_analysis.location.search_area,
													self.excluded_types.all(),
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
		self.polygon_layer = census_places.census_places(self.suitability_analysis.location.region.census_places)

		self.has_run = True
		self.save()


class RoadClassDistanceConstraintManager(UnionConstraint):
	"""
		Manages merging of the subconstraints, but then acts as a normal constraint
	"""
	merge_type = models.CharField(default="INTERSECT", choices=MERGE_CHOICES, max_length=255)  # ultimately intersected after the merging


class RoadClassDistanceConstraint(Constraint):
	merge_type = models.CharField(default="UNION", choices=MERGE_CHOICES, max_length=255)
	constraint_manager = models.ForeignKey(RoadClassDistanceConstraintManager, related_name="constraints")

	max_distance = models.IntegerField(default=1000)
	where_clause = models.TextField(default="")

	def run(self):
		roads.road_distance(self.constraint_manager.suitability_analysis.location.region.tiger_lines, self.max_distance, self.where_clause, self.constraint_manager.suitability_analysis.workspace)


class ScoredConstraint(Constraint):
	"""
		This constraint was originally meant to set manual weights, but it's on hold as of Dec 2015 since we're focusing
		on making the logistic regression model.
	"""
	merge_type = models.CharField(default="RASTER_ADD", choices=MERGE_CHOICES, max_length=255)
	scaling_factor = models.FloatField(default=1.0)

	raster_layer = models.FilePathField(null=True, blank=True)

	def rescale(self):
		"""
			After the raster is run, this function is responsible for rescaling it so that it is between 0 and scaling factor in terms of importance
		:return:
		"""

		# See http://gis.stackexchange.com/questions/50169/how-to-standardize-raster-output-from-0-to-100-using-raster-algebra

		pass
