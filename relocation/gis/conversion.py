import os
import tempfile

import arcpy

import logging
geoprocessing_log = logging.getLogger("geoprocessing")

from relocation.gis.temp import generate_gdb_filename
from relocation.gis import store_environments, reset_environments


def make_extent_from_dem(dem, output_location):
	arcpy.CheckOutExtension("Spatial")
	environements = store_environments(["mask", "extent"])

	try:
		temp_raster_filename = generate_gdb_filename(scratch=True)

		geoprocessing_log.info("Creating Constant Raster")
		arcpy.env.mask = dem
		raster = arcpy.sa.CreateConstantRaster(constant_value=1, data_type="INTEGER", cell_size=10, extent=dem)

		geoprocessing_log.info("Saving to output filename")
		raster.save(temp_raster_filename)

		geoprocessing_log.info("Converting Raster to Polygon")
		arcpy.RasterToPolygon_conversion(temp_raster_filename, output_location, simplify=False, raster_field="Value")

		arcpy.Delete_management(temp_raster_filename)

	finally:
		arcpy.CheckInExtension("Spatial")
		reset_environments(environements)


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


def features_to_dict(features, include_fields=None, exclude_fields=None):
	"""
		Takes an ArcGIS Feature class and turns it into a dictionary, excluding the Shape field

		include_fields and exclude fields are nboth meant to be lists. No conflict for using both (though it'd be silly).
		include_fields is passed to the cursor and limits it to only those fields. Error is on the user. Exclude fields
		kicks in after the cursor and is checked here.
	:param features:
	:return:
	"""

	fields = arcpy.ListFields(features)  # get the fields in the feature class

	if include_fields:
		rows = arcpy.SearchCursor(features, fields=include_fields)
	else:
		rows = arcpy.SearchCursor(features)

	feature_data_as_list_of_dicts = []

	if not exclude_fields:
		exclude_fields = []  # don't want a mutable default - leave it as none, then set it empty here so we don't have to check below

	for row in rows:  # for every row
		feature_data_as_dict = {}
		for field in fields:
			if field.name.lower() == "shape" or field.name in exclude_fields:
				continue

			feature_data_as_dict[field.name] = row.getValue(field.name)
			feature_data_as_list_of_dicts.append(feature_data_as_dict)

	return feature_data_as_list_of_dicts
