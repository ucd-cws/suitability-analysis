__author__ = 'dsx'

import os
import logging
import shutil
import traceback

import arcpy

from code_library.common import geospatial
from code_library.common.geospatial import geometry

processing_log = logging.getLogger("processing_log")


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


def centroid_near_distance(feature_class, near_feature):
	'''
		Adaptation of centroid distance code from code library to do a more basic operation by simply getting the centroid of each polygon, and then doing the same for the near features
	'''

	centroids = geometry.get_centroids(feature_class, dissolve=False)  # merge, don't append

	if len(centroids) == 0:
		processing_log.warning("No centroids generated - something probably went wrong")
		return False

	point_file = geometry.write_features_from_list(centroids, "POINT", spatial_reference=feature_class)

	near_centroid = geometry.get_centroids(near_feature, dissolve=False)  # merge, don't append

	if len(near_centroid) == 0:
		processing_log.warning("No centroids generated for near feature- something probably went wrong")
		return False

	near_point_file = geometry.write_features_from_list(near_centroid, "POINT", spatial_reference=near_feature)

	processing_log.info("Point File located at %s" % point_file)
	out_table = geospatial.generate_gdb_filename("out_table", return_full=True)
	processing_log.info("Output Table will be located at %s" % out_table)

	try:
		arcpy.PointDistance_analysis(in_features=point_file, near_features=near_point_file, out_table=out_table)
	except:
		processing_log.error("Couldn't run PointDistance - %s" % traceback.format_exc())
		return False

	return {"out_table": out_table, "point_file": point_file, }  # start just returning a dictionary instead of positional values