import logging
import os

import arcpy

from FloodMitigation.settings import BASE_DIR
geoprocessing_log = logging.getLogger("geoprocessing_log")

def mark_side_of_river(parcels, town_boundary, river):

	geoprocessing_log.info("Importing Toolbox")

	arcpy.ImportToolbox(os.path.join(BASE_DIR, "relocation", "tbx", "river_side", "river_side.tbx"), "riverside")

	geoprocessing_log.info("Marking Parcels on the same side of the river")
	arcpy.MarkParcelsOnSameSideofRiver_riverside(town_boundary,river,parcels)  # function created by ImportToolbox

	geoprocessing_log.info("Parcels marked with river side")
