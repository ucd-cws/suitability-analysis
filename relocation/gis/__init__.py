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