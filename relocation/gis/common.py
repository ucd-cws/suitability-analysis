import arcpy

def mark_polygons(polygons_to_mark, marking_polygons, field_name, selection_type="INTERSECT"):
	"""
		Takes the parcels layer for the analysis object and adds a field that it uses to mark the parcels as chosen or not chosen
	"""

	# add field - default of 0

	arcpy.AddField_management(polygons_to_mark, field_name, "SHORT")
	arcpy.CalculateField_management(polygons_to_mark, field_name, "0", expression_type="PYTHON_9.3")

	# select by location the new boundary
	marking_layer = "marking_layer"
	arcpy.MakeFeatureLayer_management(polygons_to_mark, marking_layer)

	# select the parcels that are part of the new location, and mark the "chosen" field as a true value
	try:
		arcpy.SelectLayerByLocation_management(marking_layer, selection_type, marking_polygons)

		# calculate field doesn't seem to only operate on the selection when using Python - annoying. Using Cursor instead
		parcels = arcpy.UpdateCursor(marking_layer, fields=field_name)
		for record in parcels:
			record.setValue(field_name, "1")
			parcels.updateRow(record)
	finally:
		arcpy.Delete_management(marking_layer)