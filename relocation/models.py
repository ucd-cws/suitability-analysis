from django.db import models
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.contrib import admin

# Create your models here.

import six
import sys
import logging
import os
from itertools import chain

# Get an instance of a logger
processing_log = logging.getLogger("processing_log")
geoprocessing_log = logging.getLogger("geoprocessing_log")

import arcpy

from FloodMitigation.local_settings import RUN_GEOPROCESSING, ZONAL_STATS_BUG
from FloodMitigation.settings import CHOSEN_FIELD

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
from relocation.gis import common
from relocation.gis import parcels
from relocation.gis import conversion

from FloodMitigation.settings import BASE_DIR, GEOSPATIAL_DIRECTORY, REGIONS_DIRECTORY, LOCATIONS_DIRECTORY, DEBUG

MERGE_CHOICES = (("INTERSECT", "INTERSECT"), ("ERASE", "ERASE"), ("UNION", "UNION"), ("RASTER_ADD", "RASTER_ADD"))
NLCD_LAND_COVER_CHOICES = (
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

HISTORIC_LAND_COVER_CHOICES = (  # used for remapping the numbers to categorical variables
	(1, "Water"),
	(2, "Developed"),
	(6, "Mining"),
	(7, "Barren"),
	(8, "Deciduous_Forest"),
	(9, "Evergreen_Forest"),
	(10, "Mixed_Forest"),
	(11, "Grassland"),
	(12, "Shrubland"),
	(13, "Cultivated_Cropland"),
	(14, "Hay_Pasture_land"),
	(15, "Herbaceous_Wetland"),
	(16, "Woody_Wetland"),
	(17, "Perennial_Ice_Snow"),
)


def get_field_names(read_object):
	"""
		replacement for _meta.get_all_field_names() from https://docs.djangoproject.com/en/1.9/ref/models/meta/
	"""
	return list(set(chain.from_iterable(
		(field.name, field.attname) if hasattr(field, 'attname') else (field.name,)
		for field in read_object._meta.get_fields()
		# For complete backwards compatibility, you may want to exclude
		# GenericForeignKey from the results.
		if not (field.many_to_one and field.related_model is None)
	)))


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
	extent_polygon = models.FilePathField(null=True, blank=True, editable=False)

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
	land_cover_name = models.CharField(max_length=255, )
	land_cover = models.FilePathField(null=True, blank=True, editable=False)
	census_places_name = models.CharField(max_length=255, )
	census_places = models.FilePathField(null=True, blank=True, editable=False)
	protected_areas_name = models.CharField(max_length=255, )
	protected_areas = models.FilePathField(null=True, blank=True, editable=False)
	floodplain_areas_name = models.CharField(max_length=255, )
	floodplain_areas = models.FilePathField(null=True, blank=True, editable=False)
	tiger_lines_name = models.CharField(max_length=255, )
	tiger_lines = models.FilePathField(null=True, blank=True, editable=False)
	rivers_name = models.CharField(max_length=255, )
	rivers = models.FilePathField(null=True, blank=True, editable=False)
	parcels_name = models.CharField(max_length=255, null=True, blank=True)
	parcels = models.FilePathField(null=True, blank=True, editable=False)

	# the following items are now distance rasters
	# floodplain_distance = models.FilePathField(null=True, blank=True, editable=True)
	# road_distance = models.FilePathField(null=True, blank=True, editable=True)
	# protected_areas_distance = models.FilePathField(null=True, blank=True, editable=True)

	# leveed_areas = models.FilePathField(null=True, blank=True, editable=False)

	# distance_rasters  - foreign key from distance raster object

	def make(self, **kwargs):
		"""
			provides args and then runs setup
		:return:
		"""

		for key in kwargs.keys():
			setattr(self, key, kwargs[key])

		processing_log.info("DEM is {0:s}".format(self.dem))

		self.save()

		self.setup(process_paths_from_name=False)
		self.save()

	def _base_setup(self):
		self.dem = os.path.join(str(self.layers), self.dem_name)
		self.slope = os.path.join(str(self.layers), self.slope_name)
		self.land_cover = os.path.join(str(self.layers), self.land_cover_name)
		self.census_places = os.path.join(str(self.layers), self.census_places_name)
		self.protected_areas = os.path.join(str(self.layers), self.protected_areas_name)
		self.floodplain_areas = os.path.join(str(self.layers), self.floodplain_areas_name)
		self.tiger_lines = os.path.join(str(self.layers), self.tiger_lines_name)
		self.parcels = os.path.join(str(self.layers), self.parcels_name)
		self.save()

	def setup(self, process_paths_from_name=True, do_all=True):
		"""
			Process paths from name flag indicates whether or not to take the {variable}_name fields and turn them into full paths to put in the {variable} fields.
		:param process_paths_from_name:
		:param do_all:
		:return:
		"""
		#if not (self.base_directory and self.layers):
		#	self.base_directory, self.layers = gis.create_working_directories(REGIONS_DIRECTORY, self.short_name)

		if process_paths_from_name:
			self._base_setup()

		self.check_extent()
		self.check_parcels()

		if do_all:
			self.process_derived()

	def check_extent(self):
		if not self.extent_polygon:
			if not self.dem:
				raise ValueError("Need a DEM before extent can be fixed. DEM Value is: [{0:s}]".format(self.dem))

			self.extent_polygon = generate_gdb_filename("extent_polygon", gdb=self.derived_layers)
			conversion.make_extent_from_dem(self.dem, self.extent_polygon)

			self.save()

	def _fix_parcels(self, side_length=142):
		"""
			Called when parcels layer isn't defined - generates a hexagonal mesh coveriung the region, based on the region's extent_polygon property
			default side length value comes from monroe parcels - average parcel area is 53k m2. side length of hexagon with that area is 142
		:return:
		"""

		self.parcels = generate_gdb_filename("hexagon_parcels", gdb=self.derived_layers)

		parcels.make_hexagon_tessellation(study_area=self.extent_polygon, side_length=side_length, output_location=self.parcels)
		self.save()

	def check_parcels(self):
		if self.parcels is None or self.parcels == "":
			self._fix_parcels()

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
		self.compute_major_road_distance()
		self.compute_protected_areas_distance()
		self.compute_rivers_distance()
		self.save()

	def compute_floodplain_distance(self, clear_existing=False, expand_search_area="50000 Meters"):
		self.make_distance_raster(self.floodplain_areas, "floodplain_distance", grouping="floodplains", metadata="distance to floodplain data", clear_existing=clear_existing, expand_search_area=expand_search_area)

	def compute_major_road_distance(self, clear_existing=False):
		self.make_distance_raster(self.tiger_lines, "major_road_distance", grouping="roads", metadata="Distance to road line data for this region", clear_existing=clear_existing, expand_search_area=None)

	def compute_protected_areas_distance(self, clear_existing=False, expand_search_area="80000 Meters"):
		self.make_distance_raster(self.protected_areas, "protected_distance", grouping="protected_areas", metadata="Distance to PAD-US data", clear_existing=clear_existing, expand_search_area=expand_search_area)

	def make_distance_raster(self, features, name, grouping, metadata, clear_existing=False, expand_search_area=None):

		processing_log.info("Setting up Distance Raster for {}".format(name))

		if clear_existing:
			for raster in self.distance_rasters.objects.filter(grouping=grouping):
				raster.active = False
				raster.save()

		distance_raster = DistanceRaster()
		distance_raster.region = self
		distance_raster.name = name
		distance_raster.grouping = grouping
		distance_raster.metadata = metadata

		distance_raster.path = self._compute_raster_distance(features, distance_raster.name, expand_search_area=expand_search_area)

		distance_raster.save()
		self.save()

	def compute_rivers_distance(self, clear_existing=False):

		if clear_existing:
			for raster in self.distance_rasters.objects.filter(grouping = "rivers"):
				raster.active = False
				raster.save()

		processing_log.info("Computing Rivers Distances")

		# clip the features here because otherwise it will attempt to load all of the rivers rather than just the region
		clipped_features = generate_gdb_filename("clipped_rivers", scratch=True)
		arcpy.Clip_analysis(self.rivers, self.extent_polygon, clipped_features)  # make it be only within the raster's extent before proceeding

		for upstream_area in (0,1000,10000,100000, 1000000):  # run for every stream order
			processing_log.info("Computing Distance to Streams with Upstream Area >= {}".format(upstream_area))
			new_raster = DistanceRaster()
			new_raster.grouping = "rivers"
			new_raster.region = self
			new_raster.name = "rivers_distance_UA_{}".format(upstream_area)
			new_raster.metadata = "Distance to rivers with a upstream area greater than or equal to {}".format(upstream_area)

			layer = "stream_layer"
			arcpy.MakeFeatureLayer_management(clipped_features, layer, "TotDASqKM >= {}".format(upstream_area))
			try:
				temp_features = generate_gdb_filename("temp_streams", scratch=True)

				try:
					self.check_feature_count(layer)
				except ValueError:
					processing_log.debug("Skipping making stream raster - no features in selection")
					continue  # if we get a ValueError, it means we have no features - let's not save the distance raster then!

				arcpy.CopyFeatures_management(layer, temp_features)

				new_raster.path = self._compute_raster_distance(temp_features, new_raster.name, )
			finally:
				arcpy.Delete_management(layer)  # remove the feature layer

			new_raster.save()

		self.save()

	def check_feature_count(self, features):
		count = arcpy.GetCount_management(features).getOutput(0)
		processing_log.info("Selected Features: layer has {} features".format(count))
		if int(count) == 0:
			raise ValueError("No features in feature class {}".format(features))

	def _compute_raster_distance(self, from_features, variable_name, cell_size=30, expand_search_area=None):

		arcpy.CheckOutExtension("Spatial")
		stored_environments = gis.store_environments(["mask", "extent", "cellSize", "outputCoordinateSystem"])  # back up the existing settings for environment variables
		try:
			if self.extent_polygon is None:
				raise ValueError("DEM is not defined - can't make floodplain distance because distance will be huge")

			if not expand_search_area:
				extent_polygon = self.extent_polygon
			else:
				geoprocessing_log.info("Creating expanded search window for raster distance - expanding by {}".format(expand_search_area))
				extent_polygon = generate_gdb_filename("buffered_search_area", scratch=True)
				arcpy.Buffer_analysis(self.extent_polygon, extent_polygon, buffer_distance_or_field=expand_search_area)

			processing_log.debug("Computing {} raster. Extent Polygon: {}".format(variable_name, extent_polygon))
			arcpy.env.mask = extent_polygon  # set the analysis to only occur as large as the parcels layer
			arcpy.env.extent = extent_polygon
			arcpy.env.cellSize = cell_size

			dem_spatial_reference = arcpy.Describe(self.dem).spatialReference
			arcpy.env.outputCoordinateSystem = dem_spatial_reference  # doing this because after the extent polygon used the outputCoordinateSystem environment, this started having troubles with spatial references - let's make it explicit

			geoprocessing_log.info("Computing {} Distance".format(variable_name))

			distance_raster = generate_gdb_filename("{}_{}_raster".format(self.short_name, variable_name), gdb=self.derived_layers)
			processing_log.debug("Distance raster: {0:s}".format(distance_raster))

			if RUN_GEOPROCESSING:
				processing_log.info(from_features)
				distance_raster_unsaved = arcpy.sa.EucDistance(from_features, cell_size=cell_size)
				distance_raster_unsaved.save(distance_raster)
			else:
				geoprocessing_log.warning("Skipping Geoprocessing for floodplain distance because RUN_GEOPROCESSING is False")

		finally:
			gis.reset_environments(stored_environments=stored_environments)  # restore the environment variable settings to original values
			arcpy.CheckInExtension("Spatial")

		return distance_raster

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
		return self.name

	def __unicode__(self):
		return six.u(self.name)


class DistanceRaster(models.Model):
	path = models.FilePathField()
	name = models.CharField(max_length=255)
	region = models.ForeignKey(Region, related_name="distance_rasters")
	grouping = models.CharField(max_length=50, null=True, blank=True)  # meant to be a way to group by something like "rivers"
	metadata = models.TextField()  # for noting what went into it
	active = models.BooleanField(default=True)

		
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
	

class PolygonStatistics(models.Model):
	"""
		A place to aggregate functions that operate on parcels
	"""

	layer = models.FilePathField(null=True, blank=True, editable=True)
	original_layer = models.FilePathField(null=True, blank=True, editable=True)
	id_field = models.CharField(max_length=255, default="OBJECTID", null=True, blank=True)
	geojson = models.URLField(null=True, blank=True)

	class Meta:
		abstract = True

	def setup(self):
		self.duplicate_layer()  # copy the parcels out so that we can keep a fresh copy for reprocessing still
		if RUN_GEOPROCESSING:
			#self.compute_distance_to_floodplain()
			#self.compute_distance_to_roads()
			self.compute_land_cover()
			self.compute_centroid_elevation()
			self.compute_slope_and_elevation()
			self.compute_centroid_distances()
			self.compute_distance_rasters()
			# self.mark_protected() #  Commented out because not useful
			#self.compute_distance_to_protected_areas()
		else:
			geoprocessing_log.warning("Skipping Geoprocessing for parcels because RUN_GEOPROCESSING is False")
		self.save()

		self.as_geojson()  # once processing is complete, export the geojson version so it's up to date.

	def duplicate_layer(self):
		"""
			Duplicates the parcels layer into the suitability analysis so we always have the original copy
		:return:
		"""

		analysis = self.get_analysis_object()

		new_name = arcpy.CreateUniqueName(os.path.split(self.original_layer)[1], analysis.workspace)  # get me a new name in the same geodatabase
		new_path = os.path.join(analysis.workspace, new_name)
		arcpy.CopyFeatures_management(self.original_layer, new_path)
		self.layer = new_path
		self.save()

	def get_join_field(self, zonal_table):
		"""
			A special case occurs if the id_field is OBJECTID because ArcGIS renames the field to OBJECTID_1
			This function provides that as a join field when applicable, and returns the original field otherwise
		:return:
		"""

		fields = arcpy.ListFields(zonal_table)

		for field in fields:
			if field.name == "OBJECTID_1":  # if it has an OBJECTID_1 field, return that - it might when it has OBJECTID as its key
				return "OBJECTID_1"
		else:
			return self.id_field

	def zonal_statistics(self, raster, name, statistics_type="MIN_MAX_MEAN", fields=("MIN", "MAX", "MEAN")):
		"""
			Extracts zonal statistics from a raster, and joins the min, max, and mean back to the parcels layer.
			Given a raster and a name, fields will be named mean_{name}, min_{name}, and max_{name}
		:param raster: An ArcGIS-compatible raster path
		:param name: The name to suffix fields with
		:param statistics_type: The statistics that zonal stats should generate
		:param fields: A tuple of the fields that we should pull out and rename (as stat_{field}_{name}) when we join it back
		:return: list of attribute names appended to the layer
		"""
		self.check_values()

		arcpy.CheckOutExtension("Spatial")

		analysis = self.get_analysis_object()

		geoprocessing_log.info("Running Zonal Statistics for {0:s}".format(name))
		zonal_table = generate_gdb_filename(name_base="zonal_table", gdb=analysis.workspace, scratch=False)
		processing_log.debug("Zonal Table is: {0:s}".format(zonal_table))
		processing_log.debug("Features are: {0:s}".format(self.layer))

		value_field = self.get_join_field(self.layer)

		if ZONAL_STATS_BUG:
			# there's a bug in zonal stats in ArcGIS Pro 1.2 where polygon zones create incorrect output tables
			# this works around it by rasterizing the polygon manually, then passing it into zonal stats.
			# Not setting cell size to account for data in different projections
			processing_log.debug("Doing zonal stats workaround - converting to raster")
			temp_zone_raster = generate_gdb_filename("temp_zonal_raster", scratch=True)
			zone_layer = arcpy.PolygonToRaster_conversion(self.layer, value_field=value_field, out_rasterdataset=temp_zone_raster, cell_assignment="CELL_CENTER")

			join_field = "Value"  # since we're now using a raster, the join field changes
			value_field = "Value"
		else:
			zone_layer = self.layer
			value_field = self.id_field

		processing_log.debug("Running Zonal Stats")
		arcpy.sa.ZonalStatisticsAsTable(zone_layer, value_field, raster, zonal_table, statistics_type=statistics_type)

		if not ZONAL_STATS_BUG:  # doing this here because we need to run zonal stats first to get this
			join_field = self.get_join_field(zonal_table)

		attributes = []
		try:
			geoprocessing_log.info("Joining {0:s} Zone Statistics to Parcels".format(name))

			for stat in fields:
				processing_log.info("Joining {}".format(stat))
				attribute_name = "stat_{}_{}".format(stat.lower(), name)
				gis.permanent_join(self.layer, self.id_field, zonal_table, join_field, stat, rename_attribute=attribute_name)
				attributes.append(attribute_name)
			geoprocessing_log.info("Done with joining data")
		except:
			if not DEBUG:
				geoprocessing_log.error("Unable to join zonal {0:s} back to parcels".format(name))
			else:
				six.reraise(*sys.exc_info())

		arcpy.CheckInExtension("Spatial")

		return attributes

	def rescale(self, field, offset_value):
		"""
			Runs calculate field on the given statistic field in order to rescale the values to be relative to another value. offset value is subtracted from the existing value
		"""
		if offset_value is None:
			offset_value = 0
		arcpy.CalculateField_management(self.layer, field, expression="!{0:s}! - float({1:s})".format(field, str(offset_value)), expression_type="PYTHON_9.3")

	def check_values(self):
		"""
			Just a way to check that we're ready to go since these fields aren't required initially.
		:return:
		"""
		if not self.layer:
			raise ValueError("Parcel layer (attribute: layer) is not defined - can't proceed with computations!")

		if not self.id_field:
			raise ValueError("Parcel ID/ObjectID field (attribute: id_field) is not defined - can't proceed with computations!")

	def mark_protected(self):
		analysis = self.get_analysis_object()
		common.mark_polygons(self.layer, analysis.region.protected_areas, "stat_is_protected")

	def compute_land_cover(self):

		analysis = self.get_analysis_object()
		processing_log.info("Computing land cover values")
		attributes = self.zonal_statistics(analysis.region.land_cover, "land_cover", "MAJORITY", ("MAJORITY",))
		attributes += self.zonal_statistics(analysis.region.land_cover, "land_cover", "MINORITY", ("MINORITY",))

		for attribute in attributes:
			self.remap_historic_land_cover(field=attribute)

	def remap_historic_land_cover(self, field):
		"""
			Switches the arcpy layer field full of categorical IDs to the corresponding values for historical land cover

		:param field: the field in this object's "layer" to remap
		:return:
		"""
		land_cover = {}
		for lc in HISTORIC_LAND_COVER_CHOICES:  # make a dict we can use to look things up in
			land_cover[lc[0]] = lc[1]

		temp_field_name = "temp_field_copy"

		# now we need to change the data type of the field so that we can write text values to it instead. We can't do this
		# in place, so we copy the data to a new field, drop the old field, and recreate it with a text data type before
		# we read the values from the temp field, pass them through our land cover mapping dict, then drop the temp field

		# create the new data holding field
		geoprocessing_log.info("Remapping historical land cover")
		gis.copy_field_attributes_to_new_field(source_table=self.layer, current_field=field, target_table=self.layer, target_field=temp_field_name)

		try:
			arcpy.CalculateField_management(in_table=self.layer, field=temp_field_name, expression="!{}!".format(field), expression_type="PYTHON_9.3")

			# drop the old field
			arcpy.DeleteField_management(self.layer, drop_field=[field,])

			# recreate the old field as a text type
			arcpy.AddField_management(self.layer, field, field_type="TEXT")

			geoprocessing_log.info("Reinterpreting historical land cover values...")
			# TODO: This might not work - zonal stats might make the field numeric even though we're doing a categorical measure, so we wouldn't be able to update in place
			updater = arcpy.UpdateCursor(self.layer, fields="{};{}".format(field, temp_field_name))
			for row in updater:

				try:
					value = land_cover[row.getValue(temp_field_name)]
				except KeyError:
					# if we run into errors, keep the value as is. This will help if we get stopped midway and resume - processing previously processed records will work
					value = row.getValue(temp_field_name)

				row.setValue(field, value)  # switch the number to the text version so it's categorical
				updater.updateRow(row)
		finally:
			# always drop the temp field so we can work better with the data later
			arcpy.DeleteField_management(self.layer, drop_field=[temp_field_name,])

	def compute_slope_and_elevation(self):

		analysis = self.get_analysis_object()
		self.zonal_statistics(analysis.region.dem, "elevation")
		self.zonal_statistics(analysis.region.slope, "slope")

	def compute_centroid_elevation(self):

		self.check_values()
		analysis = self.get_analysis_object()
		arcpy.CheckOutExtension("Spatial")
		new_field_name = "stat_centroid_elevation"

		processing_log.info("Computing Centroid Elevation")
		centroids = geometry.get_centroids(self.layer, as_file=True, id_field=self.id_field)
		elevation_points = generate_gdb_filename("elevation_points", scratch=True)
		arcpy.sa.ExtractValuesToPoints(centroids, analysis.region.dem, elevation_points)

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
		new_field_name = "stat_centroid_distance_to_original_boundary"

		self.check_values()
		analysis = self.get_analysis_object()
		location = analysis.get_location()

		processing_log.info("Centroid Near Distance")
		distance_information = gis.centroid_near_distance(self.layer, location.boundary_polygon, self.id_field, location.search_distance)
		try:
			processing_log.info("Permanent Join")
			gis.permanent_join(self.layer, self.id_field, distance_information["table"], "INPUT_FID", "DISTANCE", new_field_name)  # INPUT_FID and DISTANCE are results of ArcGIS, so it's safe *enough* to hard-code them.
		except:  # just trying to keep the whole program coming down if an exception is raised during processing
			if not DEBUG:
				processing_log.error("Error attaching centroid distance information - this information is currently missing from the parcels - correct your inputs or the code and reprocess the centroid distnances, or this metric will be unavailable")
			else:
				six.reraise(*sys.exc_info())

	def compute_distance_rasters(self):
		self.check_values()
		analysis = self.get_analysis_object()

		processing_log.info("Getting Distance Raster Distances")

		for distance_raster in analysis.region.distance_rasters.all():
			processing_log.info("Getting Min/Max/Mean distance to {}".format(distance_raster.name))
			self.zonal_statistics(distance_raster.path, distance_raster.name)

	def compute_distance_to_floodplain(self):

		self.check_values()
		analysis = self.get_analysis_object()

		processing_log.info("Getting Distance To Floodplain")

		self.zonal_statistics(analysis.region.floodplain_distance, "distance_to_floodplain")

	def compute_distance_to_roads(self):
		self.check_values()
		analysis = self.get_analysis_object()

		processing_log.info("Getting Distance To Roads")

		self.zonal_statistics(analysis.region.road_distance, "road_distance")

	def compute_distance_to_protected_areas(self):
		self.check_values()
		analysis = self.get_analysis_object()

		processing_log.info("Getting Distance To Protected Areas")

		self.zonal_statistics(analysis.region.protected_areas_distance, "protected_distance")

	def as_geojson(self):
		geodatabase, layer_name = os.path.split(self.layer)
		try:
			geojson_folder = os.path.join(BASE_DIR, "relocation", "static", "relocation", "geojson", self.static_folder)
			self.geojson = "relocation/geojson/{0:s}/{1:d}.geojson".format(self.static_folder, self.id)
			if not os.path.exists(geojson_folder):  # if the folder doesn't already exist
				os.makedirs(geojson_folder)  # make it

			output_file = os.path.join(geojson_folder, "{0:d}.geojson".format(self.id))  # set the full name of the output file
			geojson.file_gdb_layer_to_geojson(geodatabase, layer_name, output_file)  # run the convert
			self.save()
		except:
			if DEBUG:
				geoprocessing_log.error("Unable to convert parcels layer to geojson")
				# disabling temporarily - working on calibration - this isn't important to me right now!
				#six.reraise(*sys.exc_info())
			else:
				geoprocessing_log.error("Unable to convert parcels layer to geojson")

	def __str__(self):
		return self.original_layer

	def __unicode__(self):
		return six.u(self.original_layer)


class Parcels(PolygonStatistics):

	static_folder = "parcels"

	def get_analysis_object(self):
		try:
			return self.suitabilityanalysis
		except:
			return self.relocatedtown


class RelocationParcels(PolygonStatistics):
	static_folder = "parcels"

	def get_analysis_object(self):
		return self.relocation_analysis


class LocationInformation(PolygonStatistics):

	static_folder = "location"

	def get_analysis_object(self):
		try:
			return self.location.suitability_analysis
		except:
			relocated_statistics = self.location.cast()
			try:
				return relocated_statistics.town_before
			except:
				return relocated_statistics.town_moved


class Location(InheritanceCastModel):
	name = models.CharField(max_length=255)
	short_name = models.SlugField(blank=False, null=False)
	region = models.ForeignKey(Region, null=False)

	working_directory = models.FilePathField(path=LOCATIONS_DIRECTORY, max_length=255, allow_folders=True, allow_files=False, null=True, blank=True)
	layers = models.FilePathField(path=LOCATIONS_DIRECTORY, recursive=True, max_length=255, allow_folders=True, allow_files=False, null=True, blank=True)

	boundary_polygon_name = models.CharField(max_length=255, null=True, blank=True)
	boundary_polygon = models.FilePathField(null=True, blank=True, recursive=True, max_length=255, allow_folders=True, allow_files=False, editable=False)

	spatial_data = models.OneToOneField(LocationInformation, related_name="location")

	search_distance = models.CharField(max_length=50, default="25000 Meters")  # meters
	search_area = models.FilePathField(path=LOCATIONS_DIRECTORY, recursive=True, max_length=255, allow_folders=False, allow_files=True, null=True, blank=True, editable=False)  # storage for boundary_polygon buffered by search_distance

	def initial(self):
		"""
			Need to set up relationships before we can save the object, so this function gets run first
		:return:
		"""
		try:  # check if the related object exists
			self.spatial_data
		except LocationInformation.DoesNotExist:  # if the object doesn't exist, then create it
			spatial_data = LocationInformation()
			spatial_data.save()
			self.spatial_data = spatial_data

	def setup(self):
		"""
			setup must be run first on Suitability Analysis object!
		"""

		if not self.boundary_polygon or self.boundary_polygon == "":
			self.boundary_polygon = os.path.join(str(self.layers), self.boundary_polygon_name)

		if self.search_area is None or self.search_area == "":
			self.search_area = generate_gdb_filename("search_area", gdb=self.suitability_analysis.workspace)
			geoprocessing_log.info("Running buffer or area boundary to find search area")
			arcpy.Buffer_analysis(self.boundary_polygon, self.search_area, self.search_distance)

		# leaving the following code temporarily. I think it's no longer needed since we moved parcels to a different location
		#if self.parcels.layer is None or self.parcels.layer == "":
		#	self.parcels.layer = generate_gdb_filename(self.region.parcels_name, gdb=self.layers)
		#	geoprocessing_log.info("Copying parcels layer to location geodatabase")
		#	arcpy.CopyFeatures_management(self.region.parcels, self.parcels.layer)
		#	self.parcels.save()

		self.spatial_data.original_layer = self.boundary_polygon
		self.spatial_data.setup()  # extract the information to the boundary

		self.save()

	def __str__(self):
		return self.name

	def __unicode__(self):
		return six.u(self.name)

class Analysis(models.Model):

	name = models.CharField(max_length=255, blank=False, null=False)
	short_name = models.SlugField(blank=False, null=False)

	working_directory = models.FilePathField(path=GEOSPATIAL_DIRECTORY, max_length=255, allow_folders=True, allow_files=False, null=True, blank=True)
	workspace = models.FilePathField(path=GEOSPATIAL_DIRECTORY, recursive=True, max_length=255, allow_folders=True, allow_files=False, null=True, blank=True)

	region = models.ForeignKey(Region, related_name="%(class)s")

	# parcels layer will be copied over from the Region, but then work will proceed on it here so the region remains pure but the location starts modifying it for its own parameters
	parcels = models.OneToOneField(Parcels, related_name="%(class)s")

	class Meta:
		abstract = True

	def setup(self, force_create=False):
		self.setup_working_dirs(force_create=force_create)

		try:
			self.parcels
		except Parcels.DoesNotExist:
			processing_log.info("Creating Parcels Object")
			l_parcels = Parcels()  # pass in the parcels layer for setup
			l_parcels.original_layer = self._extract_parcels(self.region.parcels)  # extracts the parcels for this location, then passes them into the parcels object for processing
			self.parcels = l_parcels
			l_parcels.save()
			self.parcels = l_parcels  # TODO: THis is a really silly hack and seems super wrong. Need to set the value before saving the parcels object so that the relationship constraint is ok for parcels, but need to set it after saving so that the relationship constraint works for the analysis object? Silly


	def setup_working_dirs(self, force_create=False):
		if not self.working_directory or not os.path.exists(self.working_directory) or force_create:
			self.working_directory, self.workspace = gis.create_working_directories(GEOSPATIAL_DIRECTORY, self.region.short_name)
		else:
			self.workspace = os.path.join(self.working_directory, "{0:s}_layers.gdb".format(self.short_name))

		if not self.workspace or not os.path.isdir(self.workspace) or force_create:
			arcpy.CreateFileGDB_management(os.path.split(self.workspace)[0], os.path.split(self.workspace)[1])

	def __str__(self):
		return self.name

	def __unicode__(self):
		return six.u(self.name)

	def _extract_parcels(self, original_parcels):
		"""
			Takes huge parcel layers and extracts just what the current location needs for this region
		"""

		feature_layer = "parcels_layer"
		arcpy.MakeFeatureLayer_management(original_parcels, feature_layer)  # make a feature layer to use in the selection tool
		arcpy.SelectLayerByLocation_management(feature_layer, "INTERSECT", self.region.extent_polygon)  # select the features to keep - those that intersect the location

		output_name = generate_gdb_filename(name_base="parcels", gdb=self.workspace)  # make a new layer for it
		arcpy.CopyFeatures_management(feature_layer, output_name)  # write them out

		arcpy.Delete_management(feature_layer)  # get rid of the feature layer

		return output_name


class SuitabilityAnalysis(Analysis):

	result = models.FilePathField(null=True, blank=True)
	potential_suitable_areas = models.FilePathField(null=True, blank=True)
	split_potential_areas = models.FilePathField(null=True, blank=True)

	location = models.OneToOneField(Location, related_name="suitability_analysis")

	def merge(self):
		self.potential_suitable_areas = merge.merge_constraints(self.location.search_area, self.constraints.all(), self.workspace)
		self.split_potential_areas = self.split()

		self.result = self.potential_suitable_areas
		self.save()

		return self.result

	def get_location(self):
		return self.location

	def generate_mesh(self):
		"""
			TODO: Placeholder function - implement the hexagonal mesh. Need to move on and use the parcels for now)
		:return: path to feature class of the new mesh, in the location gdb
		"""

		return self.region.parcels

	def split(self):
		"""
			After the initial merge is done, this method splits up the potential areas based on the parcels (or hexagonal data)
		:return:
		"""

		if not self.potential_suitable_areas:
			processing_log.error("potential_suitable_areas is not defined - the split method can only be called after a merge has initiated, generated, and saved the potential suitable areas")
			raise ValueError("potential_suitable_areas is not defined - the split method can only be called after a merge has initiated, generated, and saved the potential suitable areas")

		if self.region.parcels:
			mesh = self.region.parcels
		else:
			mesh = self.generate_mesh()

		split_areas = generate_gdb_filename(gdb=self.workspace)
		geoprocessing_log.info("Intersecting potential areas with parcels")
		arcpy.Intersect_analysis(in_features=[self.potential_suitable_areas, self.mesh], out_feature_class=split_areas)

		return split_areas


class RelocationStatistics(Location):
	# TODO: these attributes might get moved up to PolygonStatistics at some point along with a function to extract them from the layer
	stat_centroid_elevation = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	stat_centroid_distance_to_original_boundary = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	#stat_min_distance_to_floodplain = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	#stat_max_distance_to_floodplain = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	#stat_mean_distance_to_floodplain = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	stat_min_elevation = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	stat_max_elevation = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	stat_mean_elevation = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	stat_min_slope = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	stat_max_slope = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	stat_mean_slope = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	#stat_min_road_distance = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	#stat_max_road_distance = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	#stat_mean_road_distance = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	#stat_is_protected = models.IntegerField(null=True, blank=True)
	#stat_min_protected_distance = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	#stat_max_protected_distance = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	#stat_mean_protected_distance = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)

	active = models.BooleanField(default=True)  # flag to indicate whether it can be used in an analysis

	static_folder = "relocation_towns"

	def get_analysis_object(self):
		try:
			return self.town_before
		except:
			return self.town_moved

	def read_boundary_info(self):
		"""
			Takes the processed data off of the boundary polygon and reads it back in to the attributes
		"""

		for mmm in self.min_max_means.all():
			mmm.delete()  # delete the existing min-max-means - we're going to recreate them now

		for raster in self.get_analysis_object().region.distance_rasters.all():
			min_max_mean = MinMaxMean()
			min_max_mean.relocation_statistic = self
			min_max_mean.raster = raster
			min_max_mean.save()

		processing_log.debug("Reading data for {0:s} back to object".format(self.name))
		read_fields = []
		available_fields = get_field_names(self)
		for field in available_fields:
			if field.startswith("stat_"):  # if the field is one of the ones we want to read
				read_fields.append(field)  # add it to the list of fields to read

		layer_fields = [field.name for field in arcpy.ListFields(self.spatial_data.layer)]
		common_fields = list(set(read_fields).intersection(layer_fields))  # gets rid of any fields that won't be in the data table
		for field in read_fields:
			if field not in layer_fields:
				processing_log.warning("Field {} is not available on the polygon {} for reading - probably a misspelling. Check the field name.".format(field, self.spatial_data.layer))

		polygon_data = arcpy.SearchCursor(self.spatial_data.layer)
		for record in polygon_data:  # there will only be one
			for field in common_fields:  # for all the fields we're interested in
				processing_log.info("Reading {0:s}".format(field))
				setattr(self, field, record.getValue(field))  # get the value for the field from the spatial data and set the attribute here

			for data in self.min_max_means.all():
				processing_log.info("Reading data for min_max_mean {}".format(data.raster.name))
				min_field = "stat_min_{}".format(data.raster.name)
				max_field = "stat_max_{}".format(data.raster.name)
				mean_field = "stat_mean_{}".format(data.raster.name)

				if min_field in layer_fields:
					data.min = record.getValue(min_field)

				if max_field in layer_fields:
					data.max = record.getValue(max_field)

				if mean_field in layer_fields:
					data.mean = record.getValue(mean_field)

				data.save()

	def _validate(self):
		"""
			This function exists because when entering a town, we might want to allow some attributes to be missing,
			but as of this writing a town needs to have all attributes in order to be usable.
		:return:
		"""
		for attr in get_field_names(self):
			if getattr(self, attr) is None or getattr(self, attr) == "":  # if it's blank or null
				raise ValueError("Field {0:s} is null or empty in Relocation Town {0:s} (id {0:d}). Must be resolved before this town can be used in the model".format(attr, self.name, self.id))

	def prepare(self):
		"""
			Checks all the fields and ensures they are ready to be used. If not, deactivates the town
		:return:
		"""
		try:
			self._validate()
			self.active = True
		except ValueError:
			processing_log.warning("Not using Relocation Town {0:s} due to missing attributes. Please fill in all attributes to proceed")
			self.active = False
			if DEBUG:
				six.reraise(*sys.exc_info())

		self.save()


class MinMaxMean(models.Model):
	min = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	max = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)
	mean = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=16)

	raster = models.ForeignKey(DistanceRaster, related_name="min_max_means")
	relocation_statistic = models.ForeignKey(RelocationStatistics, related_name="min_max_means", null=True, blank=True)


class RelocatedTown(Analysis):
	"""
		A class for towns that have already successfully moved that helps us store attributes for

		It's important that key attributes on this model remain the same as key attributes on the suitability analysis because
		we're going to reference this model *as* the suitability analysis from polygon statistics. So it should behave a bit like one.
		It could be worth finding some core set of functionality to subclass the two from.
	"""

	year_relocated = models.IntegerField(null=True, blank=True)
	before_structures = models.FilePathField(null=True, blank=True)
	moved_structures = models.FilePathField(null=True, blank=True)
	before_location = models.OneToOneField(RelocationStatistics, related_name="town_before")
	moved_location = models.OneToOneField(RelocationStatistics, related_name="town_moved")

	pre_move_land_cover = models.FilePathField(null=True, blank=True)

	def relocation_setup(self, name, short_name, before, after, region, make_boundaries_from_structures=False, buffer_distance="100 Meters"):
		"""
			Creates the sub-location objects and attaches them here
		:param name: Name of the city - locations will be based on this
		:param before:
		:param after_poly:
		:param region: Region object that this town/region will be attached to.
		:return:
		"""

		self.name = name
		self.short_name = short_name
		self.region = region
		self.setup()


		if make_boundaries_from_structures:
			self.before_structures = before
			self.moved_structures = after
			before_poly = self._make_boundary(before, buffer_distance, "before")
			after_poly = self._make_boundary(after, buffer_distance, "moved")
		else:
			before_poly = before
			after_poly = after

		self._make_location(before_poly, "before")
		self._make_location(after_poly, "after")

		self.save()

		self.setup_location(self.before_location)
		self.setup_location(self.moved_location)

		self.save()
		self.parcels.setup()

		self.save()

	def process_for_calibration(self, no_rescale=("stat_centroid_distance_to_original_boundary",)):
		"""

			:param no_rescale: indicates which fields should not be rescaled based on the original data
		"""
		self.mark_final_parcels()

		# scale the min max mean objects!
		for min_max_mean in self.before_location.min_max_means.all():
			for metric in ("min", "max", "mean"):
				scale_field = "stat_{}_{}".format(metric, min_max_mean.raster.name)
				value = getattr(min_max_mean, metric)
				try:
					self.rescale(scale_field, value)
				except ValueError:
					continue

		for field in get_field_names(self.before_location):
			if field.startswith("stat_") and field not in no_rescale:  # if it's a statistics field and we're supposed to rescale it
				value = getattr(self.before_location, field)
				try:
					self.rescale(field, value)
				except ValueError:
					continue

	def rescale(self, field, value):
		"""
			Given a field, it performs the rescaling of that field on the parcels data with the provided value.
			If the value is None, it raises ValueError instead
		:param field:
		:param value:
		:return:
		"""
		if value is None:
			processing_log.warning("Value for rescaling field {0:s} is None - skipping rescale".format(field))
			raise ValueError("value can't be None - skipping!")

		processing_log.info("Rescaling field {0:s} with value {1:s}".format(field, str(value)))
		self.parcels.rescale(field, value)  # get the value for the

	def get_location(self):
		return self.before_location

	def _make_boundary(self, features, buffer_distance, name_suffix=None):
		"""
			generates the boundary for an individual set of structures using a buffered convex hull.
		:param features:
		:param buffer_distance:
		:param k: saving parameter - was used for concave hulls, but now using a convex hull instead
		:return:
		"""

		processing_log.info("Making boundary from structures")
		new_layer = generate_gdb_filename(gdb="in_memory", scratch=True)
		try:
			try:
				arcpy.MinimumBoundingGeometry_management(features, new_layer, geometry_type="CONVEX_HULL")
			except:
				geoprocessing_log.error("Failed to generate polygon boundary for town {0:s} (concave_hull)".format(self.name))
				if DEBUG:
					six.reraise(*sys.exc_info())

			final_layer = generate_gdb_filename("{}_boundary_{}".format(self.name, name_suffix), gdb=self.workspace,)
			arcpy.Buffer_analysis(new_layer, final_layer, buffer_distance)
		finally:  # clean up layers
			try:
				arcpy.Delete_management(new_layer)
			except:  # doesn't matter if it fails, just log it
				geoprocessing_log.warn("failed to clean up in_memory workspace and delete concave hull generated boundary")

		return final_layer

	def mark_final_parcels(self, selection_type="INTERSECT"):
		"""
			Takes the parcels layer for the analysis object and adds a field that it uses to mark the parcels as chosen or not chosen
		"""
		common.mark_polygons(self.parcels.layer, self.moved_location.boundary_polygon, CHOSEN_FIELD)

	def _make_location(self, polygon, before_after="before", search_distance="30000 Meters"):

		location = RelocationStatistics()
		location.name = self.name
		location.short_name = self.name
		location.boundary_polygon = polygon
		location.region = self.region
		location.search_distance = search_distance
		location.layers = os.path.split(polygon)[0]
		location.boundary_polygon_name = os.path.split(polygon)[1]
		location.initial()

		if before_after == "before":
			self.before_location = location
		elif before_after == "after":
			self.moved_location = location
			self.moved_location.active = False  # will save us some time - we don't process the spatial data on inactive relocations

		location.save()  # this line is because I don't fully understand what's going on - I need to save the object before making the relationship, but I think I need to save it afterward as well.

		# TODO: This is a really silly hack and seems super wrong. Need to set the value before saving the parcels object so that the relationship constraint is ok for parcels, but need to set it after saving so that the relationship constraint works for the analysis object? Silly
		if before_after == "before":
			self.before_location = location
		elif before_after == "after":
			self.moved_location = location

	def setup_location(self, location):
		location.spatial_data.original_layer = location.boundary_polygon
		if location.active:
			location.spatial_data.setup()
			location.read_boundary_info()  # read the spatial results back to the polygon
		location.save()

	# TODO: This method needs to be refactored based on the changes to this object and its relationships
	def load_from_dict(self, dictionary, raise_errors=False):
		"""
			Given a dictionary (such as a row from a dictreader), this sets the values on this object to match the named fields in the dict
		:param dictionary:
		:return:
		"""
		for attr in get_field_names(self):
			try:
				setattr(self, attr, dictionary[attr])
			except KeyError:  # if the dictionary doesn't have this attribute
				processing_log.warning("Couldn't get attribute {0:s} from dictionary - make sure fields in the spreadsheet are named appropriately and values are defined")
				if raise_errors or DEBUG:
					six.reraise(*sys.exc_info())

	def __str__(self):
		return "Relocated Town: {0:s}".format(self.name)

	def __unicode__(self):
		return six.u("Relocated Town: {0:s}".format(self.name))


class Constraint(InheritanceCastModel):
	"""
		TODO: This probably should have been a metaclass, but wasn't - possibly worth refactoring, but this allows access to all constraints in a nice way.
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
		return self.name

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
	value = models.IntegerField(choices=NLCD_LAND_COVER_CHOICES, unique=True)

	def __str__(self):
		return self.value

	def __unicode__(self):
		return six.u(self.value)


class LandCoverConstraint(Constraint):
	merge_type = models.CharField(default="ERASE", choices=MERGE_CHOICES, max_length=255)
	excluded_types = models.ManyToManyField(LandCoverChoice)

	def run(self):
		processing_log.info("Running Land Use Constraint")
		self.polygon_layer = land_use.land_use(self.suitability_analysis.location.region.land_cover,
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

