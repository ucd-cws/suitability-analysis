__author__ = 'dsx'

import os
import logging

import arcpy

from FloodMitigation.settings import BASE_DIR

geoprocessing_log = logging.getLogger("geoprocessing")

def make_hexagon_tessellation(study_area, side_length, output_location):
	"""
		Wrapper function that imports the hexagon tool
	:param study_area:
	:param side_length:
	:param output_location:
	:return:
	"""

	geoprocessing_log.info("Importing Toolbox")

	arcpy.ImportToolbox(os.path.join(BASE_DIR,"relocation","tbx", "hexagons", "Tessellation.tbx"), "hexagonstoolbox")

	geoprocessing_log.info("Creating Hexagons")
	arcpy.CreateHexagonsBySideLength_hexagonstoolbox(study_area, side_length, output_location)  # function created by ImportToolbox

	geoprocessing_log.info("Hexagons Created!")
