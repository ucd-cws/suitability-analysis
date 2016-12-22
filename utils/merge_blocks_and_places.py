import os
import csv

import arcpy

arcpy.env.workspace = os.path.split(os.path.abspath(__file__))[0]
print("Workspace {}".format(arcpy.env.workspace))

file_mapping = os.path.join(arcpy.env.workspace, "data", "file_mapping.csv")
results_db = os.path.join(arcpy.env.workspace, "data", "results.gdb")
scratch_db = os.path.join(arcpy.env.workspace, "data", "scratch.gdb")
towns = os.path.join(arcpy.env.workspace, "data", "layers.gdb", "all_towns_v2")
results_csv = os.path.join(arcpy.env.workspace, "data", "results.csv")

results_field = "results_features"
town_field = "town_name"
pop_field = "population"

def make_field_mappings(tables):
	field_mappings = arcpy.FieldMappings()
	for table in tables:
		field_mappings.addTable(table)

	return field_mappings

def make_field_map(field_mappings, field, merge_rule="sum"):
	field_index = field_mappings.findFieldMapIndex(field)
	field_map = field_mappings.getFieldMap(field_index)
	field_map.mergeRule = merge_rule
	field_mappings.replaceFieldMap(field_index, field_map)

	return field_mappings

def make_entire_field_map(join_table, target_table, fields=("TotalLoss",)):
	field_mappings = make_field_mappings([join_table, target_table])
	for field in fields:
		field_mappings = make_field_map(field_mappings, field, "sum")

	return field_mappings


results = []

with open(file_mapping, 'r') as csv_file:
	rows = csv.DictReader(csv_file, fieldnames=[town_field, results_field, pop_field],)

	print("Getting Set Up")
	town_layer = "all_towns"
	arcpy.MakeFeatureLayer_management(towns, town_layer)
	try:
		for row in rows:
			if row[town_field] == town_field:  # I can't find how to get it to skip the header right now
				continue  # so if it looks like we're in the header, skip the row

			print("Processing {}".format(row[town_field]))

			# select town by attribute - export to new polygon
			arcpy.SelectLayerByAttribute_management(town_layer, "NEW_SELECTION", "NAME='{}'".format(row[town_field]))
			town_name_safe = row[town_field].replace(" ", "_")
			town_name_safe = town_name_safe.replace("-", "_")
			town_export = arcpy.CreateUniqueName(town_name_safe, scratch_db)
			arcpy.CopyFeatures_management(town_layer, town_export)

			arcpy.MakeFeatureLayer_management(town_export, town_name_safe)
			results_layer = "{}_results".format(row[results_field])
			arcpy.MakeFeatureLayer_management(os.path.join(results_db, row[results_field]), results_layer)
			try:
				# select blocks with their center in the town, export to new feature class
				arcpy.SelectLayerByLocation_management(results_layer, "HAVE_THEIR_CENTER_IN", town_name_safe)
				results_export = arcpy.CreateUniqueName("{}_census_blocks".format(row[results_field]), scratch_db)
				arcpy.CopyFeatures_management(results_layer, results_export)
			finally:
				arcpy.Delete_management(town_name_safe)
				arcpy.Delete_management(results_layer)

			# spatial join blocks to town
			loss_field = "TotalLoss"
			spatial_join = arcpy.CreateUniqueName("{}_with_results".format(town_name_safe), scratch_db)
			field_map = make_entire_field_map(town_export, results_export, fields=(loss_field,))
			arcpy.SpatialJoin_analysis(town_export, results_export, spatial_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", field_map)

			# sum the total damages - remember they're in 1000s
			damages = 0
			with arcpy.da.SearchCursor(spatial_join, loss_field) as cursor:
				for cursor_row in cursor:
					damages = damages + cursor_row[0]

			damages = damages*1000  # make the units normal

			# make a new total by population
			pop_normalized = float(damages) / float(row[pop_field])

			# add row to results dict for damages total and by pop
			print("Damages: {}, Per Capita: {}".format(damages, pop_normalized))
			result = {"town": row[town_field], "damages": damages, "per_capita_damages": pop_normalized}
			results.append(result)

	finally:  # delete town layer on any sort of crash/exit - helps in interactive interpreter
		arcpy.Delete_management(town_layer)


with open(results_csv, 'w') as csv_file:
	writer = csv.DictWriter(csv_file, fieldnames=["town", "damages", "per_capita_damages"],)
	writer.writeheader()
	writer.writerows(results)