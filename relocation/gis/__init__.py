__author__ = 'dsx'

import os
import logging
import shutil
import traceback

import arcpy

from relocation.gis import geometry

processing_log = logging.getLogger("processing_log")
geoprocessing_log = logging.getLogger("geoprocessing_log")

from relocation.gis import temp
from FloodMitigation import local_settings
temp.temp_gdb = local_settings.SCRATCH_GDB


def create_working_directories(base_folder, folder_name):

	gdb_name = "layers.gdb"
	working_directory = os.path.join(base_folder, folder_name)

	if os.path.exists(working_directory):
		processing_log.warning("processing directory for project already exists - deleting!")
		shutil.rmtree(working_directory)

	os.mkdir(working_directory)
	arcpy.CreateFileGDB_management(working_directory, gdb_name)
	workspace = os.path.join(working_directory, gdb_name)

	return working_directory, workspace


def store_environments(environments_list):
	"""
		Given an iterable of environment variables for arcpy, it stores the current values into a dictionary so they can be reset after an operation
	:param environments_list:
	:return:
	"""
	stored_environments = {}
	for env in environments_list:
		stored_environments[env] = arcpy.env.__getitem__(env)

	return stored_environments


def reset_environments(stored_environments):
	"""
		Given a dict of stored environment variables (from store_environments), it resets the environment values to the value in the dictionary
	:param stored_environments:
	:return:
	"""
	for env in stored_environments.keys():
		arcpy.env.__setitem__(env, stored_environments[env])


def centroid_near_distance(feature_class, near_feature, id_field, search_radius=1000):
	"""
		Adaptation of centroid distance code from code library to do a more basic operation by simply getting the centroid of each polygon,
		and then doing the same for the near features
	"""

	if not feature_class or not near_feature:
		raise ValueError("missing the feature class or the near feature - both arguments must be defined!")

	centroids = geometry.get_centroids(feature_class, dissolve=False, id_field=id_field)  # merge, don't append

	if not centroids:
		processing_log.info("No centroids generated - something probably went wrong")
		return False

	processing_log.info("first centroids retrieved")

	temp_filename = arcpy.CreateScratchName("temp", workspace=r"C:\Users\dsx.AD3\Documents\ArcGIS\scratch.gdb")
	processing_log.info("{0:s}".format(temp_filename))
	point_file = geometry.write_features_from_list(centroids, "POINT", filename=temp.generate_gdb_filename(), spatial_reference=feature_class, write_ids=True)
	processing_log.info("first centroids written")

	near_centroid = geometry.get_centroids(near_feature, dissolve=False)  # merge, don't append

	processing_log.info("second centroids retrieved")
	if not near_centroid:
		processing_log.info("No centroids generated for near feature- something probably went wrong")
		return False

	near_point_file = geometry.write_features_from_list(near_centroid, "POINT", spatial_reference=near_feature)
	processing_log.info("second centroids written")

	processing_log.info("Point File located at {0!s}".format(point_file))  # change back to info
	out_table = temp.generate_gdb_filename("out_table", return_full=True)
	processing_log.info("Output Table will be located at {0!s}".format(out_table))  # change back to info

	try:
		arcpy.PointDistance_analysis(in_features=point_file, near_features=near_point_file, out_table=out_table, search_radius=search_radius)
	except:
		processing_log.error("Couldn't run PointDistance - {0!s}".format(traceback.format_exc()))
		return False

	return {"table": out_table, "point_file": point_file, }  # start just returning a dictionary instead of positional values


def permanent_join(target_table, target_attribute, source_table, source_attribute, attribute_to_attach, rename_attribute=None):
	"""
	Provides a way to permanently attach a field to another table, as in a one to one join, but without performing a
	join then exporting a new dataset. Operates in place by creating a new field on the existing dataset.

	Or, in other words, Attaches a field to a dataset in place in ArcGIS - instead of the alternative of doing an
	actual join and then saving out a new dataset. Only works as a one to one join.

	:param target_table: the table to attach the joined attribute to
	:param target_attribute: the attribute in the table to base the join on
	:param source_table: the table containing the attribute to join
	:param source_attribute: the attribute in table2 to base the join on
	:param attribute_to_attach: the attribute to attach to table 1
	:param rename_attribute: string to indicate what to rename the field as when it's joined.
	:return: None
	"""

	# first, we need to find the information about the field that we're attaching
	join_table_fields = arcpy.ListFields(source_table)
	for field in join_table_fields:
		if field.name == attribute_to_attach:  # we found our attribute
			base_field = field
			break
	else:
		raise ValueError("Couldn't find field to base join on in source table")

	type_mapping = {"Integer": "LONG", "OID": "LONG", "SmallInteger": "SHORT", "String": "TEXT"}  # ArcGIS annoyingly doesn't report out the same data types as you need to provide, so this allows us to map one to the other
	if base_field.type in type_mapping.keys():  # if it's a type that needs conversion
		new_type = type_mapping[base_field.type]  # look it up and save it
	else:
		new_type = base_field.type.upper()  # otherwise, just grab the exact type as specified

	if rename_attribute:
		new_name = rename_attribute
	else:
		new_name = base_field.name

	# copy the field over other than those first two attributes
	arcpy.AddField_management(target_table, new_name, new_type, field.precision, field.scale, field.length, field_alias=None, field_is_nullable=field.isNullable, field_is_required=field.required, field_domain=field.domain)

	join_data = read_field_to_dict(source_table, attribute_to_attach, source_attribute)  # look up these values so we can easily just use one cursor at a time - first use the search cursor, then the update cursor on the new table

	updater = arcpy.UpdateCursor(target_table)
	for row in updater:
		if row.getValue(target_attribute) in join_data.keys():  # since we might not always have a match, we need to check, this should speed things up too
			row.setValue(new_name, join_data[row.getValue(target_attribute)])  # set the value for the new field to the other table's value for that same field, indexed by key
			updater.updateRow(row)

	del updater


def read_field_to_dict(input_table, data_field, key_field):
	"""
		Given an arcgis table and a field containing keys and values, reads that field into a dict based on the key field
	:param table: an ArcGIS table (or feature class, etc)
	:param data_field: the field that contains the data of interest - these values will be the dictionary values
	:param key_field: the field that contains the keys/pkey values - these values will be the keys in the dictionary
	:return: dict of the data loaded from the table
	"""

	data_dict = {}

	rows = arcpy.SearchCursor(input_table)
	for row in rows:
		data_dict[row.getValue(key_field)] = row.getValue(data_field)

	del rows

	return data_dict
