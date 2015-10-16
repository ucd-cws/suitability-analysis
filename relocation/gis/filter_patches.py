__author__ = 'nickrsan'

import arcpy

from code_library.common import geospatial


def filter_small_patches(raster_dataset, patch_area=9000, area_length_ratio=4, filter_value=0):
	"""
		Given a boolean 0/1 raster, filters out patches that are either too small, or which are not compact
	:param raster_dataset: An ArcGIS compatible raster dataset
	:param patch_area: The minimum area to keep a patch, in square units of the raster's projection. Patches smaller than this will be removed.
	:param area_length_ratio: The ratio of area to perimeter (Area/Perimeter) under which patches will be removed.
	:param filter_value: The value in the grid which will be kept - other grid features will be removed.
	:return: Feature class converted from raster with patches removed when they don't match the filter_value, or when they are smaller than patch_area, or when their area to perimeter ratio is smaller than specified.
	"""
	# confirm we have a raster layer
	desc = arcpy.Describe(raster_dataset)
	if desc.dataType != "RasterDataset":
		raise TypeError("parameter raster_layer must be of type RasterDataset")

	del desc

	# convert raster to polygon
	raster_poly = geospatial.generate_gdb_filename("fil", scratch=True)
	arcpy.RasterToPolygon_conversion(raster_dataset, raster_poly, simplify=False, raster_field="Value")

	# remove polygons that we're not looking at (value == 1)
	working_layer = "working_layer"
	arcpy.MakeFeatureLayer_management(raster_poly, working_layer, where_clause="gridcode = {0:s}".format(filter_value))  # load a feature layer and remove the polygons we're not interested in in a single step

	# remove polygons that are too small (smaller than patch_area)
	arcpy.SelectLayerByAttribute_management(working_layer, "NEW_SELECTION", where_clause="Shape_Area > {0:s}".format(patch_area))

	# export to new layer for passing off to remove_non_compact_polys
	first_filtered_poly = geospatial.generate_gdb_filename("filter_patches", scratch=True)
	arcpy.CopyFeatures_management(working_layer, first_filtered_poly)
	arcpy.Delete_management(working_layer)  # delete it, then create a new layer with the same name to pass to the next function

	arcpy.MakeFeatureLayer_management(first_filtered_poly, working_layer)

	# run remove_non_compact_polys to remove polygons that aren't compact
	filtered_features = remove_non_compact_polys(working_layer, area_length_ratio=area_length_ratio)

	# return the polygons
	return filtered_features


def remove_non_compact_polys(feature_layer, area_length_ratio=1):

	desc = arcpy.Describe(feature_layer)
	if desc.dataType != "FeatureLayer":
		feature_class = feature_layer
		feature_layer = "working_layer"
		delete_layer = True
		arcpy.MakeFeatureLayer_management(feature_class, feature_layer)
	else:
		delete_layer = False

	ratio_field = "area_permiter_ratio"
	arcpy.AddField_management(feature_layer, ratio_field, "DOUBLE")

	arcpy.CalculateField_management(feature_layer, ratio_field, "!Shape_Area!/!Shape_Length!", "PYTHON_9.3")

	# remove polygons that are too small (smaller than patch_area)
	arcpy.SelectLayerByAttribute_management(feature_layer, "NEW_SELECTION", where_clause="ratio_field > {0:s}".format(area_length_ratio))
	filtered_poly = geospatial.generate_gdb_filename("filter_patches", scratch=False)
	arcpy.CopyFeatures_management(feature_layer, filtered_poly)

	if delete_layer:
		arcpy.Delete_management(feature_layer)

	return filtered_poly