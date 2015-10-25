__author__ = 'dsx'

import os
import logging
import shutil

import arcpy

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
		stored_environments[env] = arcpy.env.__dict__[env]

	return stored_environments

def reset_environments(stored_environments):
	"""
		Given a dict of stored environment variables (from store_environments), it resets the environment values to the value in the dictionary
	:param stored_environments:
	:return:
	"""
	for env in stored_environments.keys():
		arcpy.env.__dict__[env] = stored_environments[env]