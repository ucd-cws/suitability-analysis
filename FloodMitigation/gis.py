import os
import logging
import shutil

import arcpy

processing_log = logging.getLogger("processing_log")

def clean_location(path, path_type="FGDB"):
	"""
		Copied from PISCES 2.0.4
		Cleans and recreates a particular type of workspace. Types include file geodatabases, personal geodatabases, and folders
	:param path: the full path to the item to clean
	:param path_type: one of the following: (FGDB, PGDB, Folder) for File Geodatabase, Personal Geodatabase, and folders, respectively
	:return:
	"""

	processing_log.info("Recreating {0:s}".format(path))
	if path_type not in ("FGDB", "PGDB", "Folder"):
		raise ValueError("path_type must be one of (FGDB, PGDB, Folder)")

	if path_type == "Folder":
		if os.path.exists(path):  # delete the folder if it exists
			shutil.rmtree(path)

		os.mkdir(path)  # then recreate it
	else:
		if arcpy.Exists(path):  # if we have a GDB, delete it
			arcpy.Delete_management(path)

		path_parts = os.path.split(path)  # Now recreate it based on type
		if path_type == "FGDB":
			arcpy.CreateFileGDB_management(path_parts[0], path_parts[1])  # then recreate it - fastest way to compact a temp GDB
		elif path_type == "PGDB":
			arcpy.CreatePersonalGDB_management(path_parts[0], path_parts[1])