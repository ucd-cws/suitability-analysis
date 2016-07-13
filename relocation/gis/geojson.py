import os
import logging

import arcpy

from relocation.gis import temp
from FloodMitigation.settings import REPROJECTION_ID
geoprocessing_log = logging.getLogger("geoprocessing")


def file_gdb_layer_to_geojson(geodatabase, layer_name, outfile):

	geoprocessing_log.info("Converting layer to geojson")
	if os.path.exists(os.path.join(outfile)):
		geoprocessing_log.warn("Output file {0:s} exists - Deleting".format(outfile))
		os.remove(outfile)

	geoprocessing_log.info("Reprojecting to web_mercator")
	reprojected = temp.generate_gdb_filename(layer_name)
	arcpy.Project_management(in_dataset=os.path.join(geodatabase, layer_name), out_dataset=reprojected, out_coor_system=arcpy.SpatialReference(REPROJECTION_ID))

	geoprocessing_log.info("Writing out geojson file at {0:s}".format(reprojected))
	arcpy.FeaturesToJSON_conversion(reprojected, outfile, geoJSON="GEOJSON")  # export GeoJSON with ArcGIS Pro

	return  #  skip the code below for now, but retain it for legacy purposes for now. Can probably delete after August 2016. It was replaced by the line above

	ogr.UseExceptions()

	geoprocessing_log.debug("Opening FGDB")
	file_gdb_driver = ogr.GetDriverByName("OpenFileGDB")
	new_gdb, new_layer_name = os.path.split(reprojected)
	gdb = file_gdb_driver.Open(new_gdb, 0)

	geojson_driver = ogr.GetDriverByName("GeoJSON")
	geojson = geojson_driver.CreateDataSource(outfile)

	geoprocessing_log.info("Writing out geojson file at {0:s}".format(new_layer_name))
	layer = gdb.GetLayer(new_layer_name)
	geojson.CopyLayer(layer, layer_name, options=["COORDINATE_PRECISION=4",])
