__author__ = 'nickrsan'

import logging
import arcpy
from code_library.common import geospatial
from relocation.gis.filter_patches import convert_and_filter_by_code

logger = logging.getLogger("relocation.suitability.processing")


def process_local_slope(dem=None, slope=None, max_slope=30, mask=None, return_type="polygon"):
	"""

	:param dem: The DEM to process
	:param slope: If slope is already processed, use this instead.
	:param max_slope: The maximum slope in degrees that will be considered suitable for building
	:param mask: A polygon or raster mask to use as the processing area (arcpy.env.mask/Analysis Mask environment)
	:param return_type: whether to return a polygon feature class or a raster. Default is polygon, where raster will be processed to polygon automatically. Options are "polygon" or "raster"
	:return:
	"""

	if not dem and not slope:
		raise ValueError("Must provide either a slope raster or a DEM raster. Either parameter 'dem' or parameter 'slope' must be defined.")

	arcpy.CheckOutExtension("Spatial")

	if not slope:
		arcpy.env.mask = mask
		logger.info("Processing raster to slope")
		mask_raster = arcpy.sa.ExtractByMask(dem, mask)  # mask environment variable hasn't been working - force extraction
		slope_raster = arcpy.sa.Slope(mask_raster, output_measurement="DEGREE")
	else:
		slope_raster = arcpy.sa.ExtractByMask(slope, mask)  # mask environment variable hasn't been working - force extraction

	logger.info("Thresholding raster")
	threshold_raster = slope_raster < max_slope

	raster_name = geospatial.generate_gdb_filename("slope_raster")

	logger.info("Saving raster to disk")
	threshold_raster.save(raster_name)

	arcpy.CheckInExtension("Spatial")

	if return_type.lower() == "polygon":

		logger.info("Converting to polygons")
		new_name = convert_and_filter_by_code(raster_name, filter_value=1)

		return new_name
	elif return_type.lower() == "raster":
		return raster_name
	else:
		raise ValueError("Invalid parameter for return_type. Must be either \"raster\" or \"polygon\"")