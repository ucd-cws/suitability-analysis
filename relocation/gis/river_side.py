import logging
import os

import arcpy

from relocation.gis.temp import generate_gdb_filename

from FloodMitigation.settings import BASE_DIR
geoprocessing_log = logging.getLogger("geoprocessing_log")


def mark_side_of_river(parcels, town_boundary, rivers):

	river_field = "is_river"
	correct_side_field = "stat_is_on_correct_side_of_river"
	dissolved_polygon_layer = "dissolved_polygon_layer"
	parcels_layer = "parcels_layer"

	# Process: Remove fields if they already exist - simpler
	fields = [field.name for field in arcpy.ListFields(parcels)]
	if river_field in fields:
		arcpy.DeleteField_management(parcels, river_field)
	if correct_side_field in fields:
		arcpy.DeleteField_management(parcels, correct_side_field)

	arcpy.AddField_management(parcels, river_field, "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
	arcpy.CalculateField_management(parcels, river_field, "0", "PYTHON_9.3", "")

	# Process: Add Correct Side Field
	arcpy.AddField_management(parcels, correct_side_field, "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
	arcpy.CalculateField_management(parcels, correct_side_field, "0", "PYTHON_9.3", "")

	arcpy.MakeFeatureLayer_management(parcels, parcels_layer)
	arcpy.SelectLayerByLocation_management(parcels_layer, "INTERSECT", rivers, "", "NEW_SELECTION", "NOT_INVERT")
	arcpy.CalculateField_management(parcels_layer, "is_river", "1", "PYTHON_9.3", "")

	arcpy.SelectLayerByLocation_management(parcels_layer, "INTERSECT", parcels_layer, "", "SWITCH_SELECTION", "NOT_INVERT")

	dissolved_parcels = generate_gdb_filename("dissolved_parcels")
	arcpy.Dissolve_management(parcels_layer, dissolved_parcels, "is_river", "", "SINGLE_PART", "DISSOLVE_LINES")

	arcpy.MakeFeatureLayer_management(dissolved_parcels, dissolved_polygon_layer)

	correct_side_on_disk = generate_gdb_filename("correct_side_on_disk")
	arcpy.SelectLayerByLocation_management(dissolved_polygon_layer, "INTERSECT", town_boundary, "", "NEW_SELECTION", "NOT_INVERT")
	arcpy.CopyFeatures_management(dissolved_polygon_layer, correct_side_on_disk)

	arcpy.SelectLayerByLocation_management(parcels_layer, "INTERSECT", correct_side_on_disk, "", "NEW_SELECTION", "NOT_INVERT")
	arcpy.CalculateField_management(parcels_layer, correct_side_field, "1", "PYTHON_9.3", "")
