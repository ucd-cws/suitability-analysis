__author__ = 'nickrsan'

import logging
import arcpy
from code_library.common import geospatial
from relocation.gis.filter_patches import convert_and_filter_by_code

logger = logging.getLogger("relocation.suitability.processing")


def process_local_slope(dem, max_slope, mask, return_type="polygon"):
	"""

	:param dem: The DEM to process
	:param max_slope: The maximum slope in degrees that will be considered suitable for building
	:param mask: A polygon or raster mask to use as the processing area (arcpy.env.mask/Analysis Mask environment)
	:param return_type: whether to return a polygon feature class or a raster. Default is polygon, where raster will be processed to polygon automatically. Options are "polygon" or "raster"
	:return:
	"""
	arcpy.CheckOutExtension("Spatial")

	arcpy.env.mask = mask
	logger.info("Processing raster to slope")
	slope_raster = arcpy.sa.Slope(dem, output_measurement="DEGREE")

	logger.info("Thresholding raster")
	threshold_raster = slope_raster < max_slope

	raster_name = geospatial.generate_gdb_filename("slope_raster")

	logger.info("Saving raster to disk")
	threshold_raster.save(raster_name)

	arcpy.CheckInExtension("Spatial")

	if return_type == "polygon":

		logger.info("Converting to polygons")
		new_name = convert_and_filter_by_code(raster_name, filter_value=0)

		return new_name
	elif return_type == "raster":
		return raster_name
	else:
		raise ValueError("Invalid parameter for return_type. Must be either \"raster\" or \"polygon\"")