import os
import sys
import traceback
import logging
import tempfile

import arcpy

temp_folder = None
temp_gdb = None

temp_datasets = []

geoprocessing_log = logging.getLogger("geoprocessing")


def generate_gdb_filename(name_base="xt", return_full=True, gdb=None, scratch=False):
	'''returns the filename and the gdb separately for use in some tools'''
	if gdb is None:
		temp_gdb = get_temp_gdb()
	else:
		temp_gdb = gdb

	try:
		if scratch:
			filename = arcpy.CreateScratchName(name_base, workspace=temp_gdb)
		else:
			filename = arcpy.CreateUniqueName(name_base, temp_gdb)
	except:
		geoprocessing_log.error("Couldn't create GDB filename - {0:s}".format(traceback.format_exc()))
		raise

	temp_datasets.append(filename)  # add it to the tempfile registry

	if return_full:
		return filename
	else:
		return os.path.split(filename)[1], temp_gdb


def make_temp(override=False):
	"""
		override enables us to say just "give me a new temp gdb and don't try to manage it"
	"""

	global temp_gdb
	global temp_folder
	global raster_count

	if not override:
		if temp_gdb and raster_count < 100:
			raster_count += 1
			return temp_folder, temp_gdb
		else:
			raster_count = 0

	try:
		temp_folder = tempfile.mkdtemp()
		temp_gdb = os.path.join(temp_folder, "temp.gdb")
		if not arcpy.Exists(temp_gdb):
			if 'log' in sys.modules:
				geoprocessing_log.write("Creating {0:s}".format(temp_gdb))
			arcpy.CreateFileGDB_management(temp_folder, "temp.gdb")
			return temp_folder, temp_gdb
	except:
		return False, False


def get_temp_folder():
	temp_folder, temp_gdb = make_temp()
	if temp_folder:
		return temp_folder
	else:
		raise IOError("Couldn't create temp gdb or folder")

def get_temp_gdb():

	temp_folder, temp_gdb = make_temp()
	if temp_gdb:
		return temp_gdb
	else:
		raise IOError("Couldn't create temp gdb or folder")