__author__ = 'dsx'

import arcpy
import logging

from code_library.common.geospatial import generate_gdb_filename

geoprocessing_log = logging.getLogger("geoprocessing")

def merge(existing_areas, change_areas, workspace, method="ERASE"):
	"""

	:param existing_areas: The existing valid areas (as a feature class)
	:param change_areas: The areas to modify - they can either be remaining suitable areas (INTERSECT) or areas to remove (ERASE)
	:param method: the method to use for interacting the two layers, ERASE or INTERSECT. ERASE is default and removes areas from existing_areas when they are present in change_areas
	:return:
	"""

	if method != "ERASE" and method != "INTERSECT":
		raise ValueError("argument 'method' to merge function is invalid. Must be either 'ERASE' or 'INTERSECT'")

	new_features = generate_gdb_filename("suitable_areas", return_full=True, gdb=workspace)
	if method == "ERASE":
		geoprocessing_log.info("Erasing features")
		arcpy.Erase_analysis(existing_areas, change_areas, new_features)
	elif method == "INTERSECT":
		geoprocessing_log.info("Intersecting features")
		arcpy.Intersect_analysis(existing_areas, change_areas)

	return new_features