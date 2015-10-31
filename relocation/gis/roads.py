__author__ = 'dsx'

import arcpy
import logging

from code_library.common.geospatial import generate_gdb_filename

geoprocessing_log = logging.getLogger("geoprocessing")
processing_log = logging.getLogger("processing")


def road_distance(roads_layer, max_distance, roads_layer_where_clause, workspace):
	"""
		Given a roads layer, it loads the roads specified in the where clause, then buffers the roads to max_distance, returning the buffered feature class
	:param roads_layer:
	:param max_distance:
	:param roads_layer_where_clause:
	:param workspace:
	:return:
	"""


	feature_layer = "roads_layer"
	arcpy.MakeFeatureLayer_management(roads_layer, feature_layer, roads_layer_where_clause)

	roads_buffered = generate_gdb_filename("roads_buffer", gdb=workspace)
	arcpy.Buffer_analysis(feature_layer, roads_buffered, max_distance)

	arcpy.Delete_management(feature_layer)

	return roads_buffered