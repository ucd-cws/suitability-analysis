import os
import tempfile

import arcpy

import logging
geoprocessing_log = logging.getLogger("geoprocessing")

from relocation.gis.temp import generate_gdb_filename
from relocation.gis import store_environments, reset_environments


def make_extent_from_dem(dem, output_location):
	arcpy.CheckOutExtension("Spatial")
	environments = store_environments(["mask", "extent", "outputCoordinateSystem"])

	try:
		temp_raster_filename = generate_gdb_filename(scratch=True)

		dem_properties = arcpy.Describe(dem)
		arcpy.env.outputCoordinateSystem = dem_properties.spatialReference  # set the spatial reference environment variable so that the constant raster gets created properly

		geoprocessing_log.info("Creating Constant Raster")
		arcpy.env.mask = dem
		raster = arcpy.sa.CreateConstantRaster(constant_value=1, data_type="INTEGER", cell_size=10, extent=dem)

		geoprocessing_log.info("Saving to output filename")
		print(temp_raster_filename)
		raster.save(temp_raster_filename)

		geoprocessing_log.info("Converting Raster to Polygon")
		arcpy.RasterToPolygon_conversion(temp_raster_filename, output_location, simplify=False, raster_field="Value")

		#arcpy.Delete_management(temp_raster_filename)

	finally:
		arcpy.CheckInExtension("Spatial")
		reset_environments(environments)


def convert_to_temp_csv(features):
	"""
		Just a helper function that exports an ArcGIS table to a temporary csv file and returns the path
	:param features:
	:return:
	"""
	filepath = tempfile.mktemp(".csv", prefix="arcgis_csv_table")
	folder, filename = os.path.split(filepath)
	arcpy.TableToTable_conversion(features, folder, filename)
	return filepath


def features_to_dicts(features, chosen_field, none_to=0, exclude_fields=()):
	fields = arcpy.ListFields(features)  # get the fields in the feature class

	fields_to_include = [chosen_field]
	for field in fields:  # get all of the fields that start with "stat"
		if field.name.startswith("stat_") and field.name not in exclude_fields:
			fields_to_include.append(field.name)

	all_feature_data = []

	rows = arcpy.SearchCursor(features, fields=";".join(fields_to_include))
	for row in rows:  # for every row
		feature_data = {}

		for field in fields_to_include:
			value = row.getValue(field)
			if value is None:
				value = none_to  # set the value as what we want to convert None objects to

			feature_data[field] = value

		all_feature_data.append(feature_data)

	return all_feature_data


def features_to_dict_or_array(features, include_fields=None, exclude_fields=None, array=False, none_to=0):
	"""
		Takes an ArcGIS Feature class and turns it into a dictionary or multidimensional list, excluding the Shape field

		when array == True, it makes a list of lists (suitable for sklearn), when False, it makes a list of dicts (suitable for CSVs)

		include_fields and exclude fields are both meant to be lists. No conflict for using both (though it'd be silly).
		include_fields is passed to the cursor and limits it to only those fields. Error is on the user. Exclude fields
		kicks in after the cursor and is checked here.C:\
	:param features:
	:return:
	"""

	fields = arcpy.ListFields(features)  # get the fields in the feature class
	if include_fields:
		real_fields = [field.name for field in fields]
		to_include = list(set(real_fields).intersection(set(include_fields)))
		include = ";".join(to_include)  # include only the fields that exist and then semicolon separate
		geoprocessing_log.debug("include string is {0:s}".format(include))
		rows = arcpy.SearchCursor(features, fields=include)
	else:
		rows = arcpy.SearchCursor(features)

	all_feature_data = []

	if not exclude_fields:
		exclude_fields = []  # don't want a mutable default - leave it as none, then set it empty here so we don't have to check below

	for row in rows:  # for every row
		if array:
			feature_data = []
		else:
			feature_data = {}

		for field in fields:
			if include_fields and field.name not in include_fields:
				continue
			if field.name.lower() == "shape" or field.name in exclude_fields:
				continue

			value = row.getValue(field.name)
			if value is None:
				value = none_to  # set the value as what we want to convert None objects to

			if array:
				feature_data.append(value)
			else:
				feature_data[field.name] = value

		all_feature_data.append(feature_data)

	return all_feature_data