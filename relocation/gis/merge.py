__author__ = 'dsx'

import arcpy
import logging
import traceback

from code_library.common.geospatial import generate_gdb_filename

geoprocessing_log = logging.getLogger("geoprocessing")
processing_log = logging.getLogger("processing")

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
		arcpy.Intersect_analysis([existing_areas, change_areas], new_features)
	elif method == "UNION":
		geoprocessing_log.info("Unioning features")
		arcpy.Union_analysis([existing_areas, change_areas], new_features)  # existing areas should be a list already

	return new_features


def merge_constraints(suitable_areas, constraints, workspace):
	for constraint in constraints:
		full_constraint = constraint.cast()  # get the subobject

		if not full_constraint.enabled:
			continue
		if not full_constraint.has_run:  # basically, is the constraint ready to merge? We need to preprocess some of them
			try:
				full_constraint.run()  # run constraint
			except:
				processing_log.error(
					"Error running constraint for {0:s}. Processing will proceed to run other constraints and merge completed constraints. To incorporate this constraint, corrections to user paramters or code may be necessary. Python reported the following error: {1:s}".format(
						full_constraint.name, traceback.format_exc(3)))
				continue  # don't try to merge if we couldn't create the layer

		try:
			suitable_areas = merge(suitable_areas, full_constraint.polygon_layer, workspace, full_constraint.merge_type)
		except:
			processing_log.error(
				"Failed to merge constraint {0:s} with previous constraints! Processing will proceed to run other constraints and merge completed constraints. Python reported the following error: {1:s}".format(
					full_constraint.name, traceback.format_exc(3)))