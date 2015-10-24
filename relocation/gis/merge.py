__author__ = 'dsx'

import arcpy

from code_library.common.geospatial import generate_gdb_filename

def merge(existing_areas, change_areas, workspace, method="ERASE"):
	"""

	:param existing_areas: The existing valid areas (as a feature class)
	:param change_areas: The areas to modify - they can either be remaining suitable areas (INTERSECT) or areas to remove (ERASE)
	:param method: the method to use for interacting the two layers, ERASE or INTERSECT. ERASE is default and removes areas from existing_areas when they are present in change_areas
	:return:
	"""

	if method != "ERASE" and method != "INTERSECT":
		raise ValueError("argument 'method' to merge function is invalid. Must be either 'ERASE' or 'INTERSECT'")

	if method == "ERASE":
