__author__ = 'dsx'

import logging

import arcpy

from relocation.gis.temp import generate_gdb_filename

from relocation.gis import store_environments, reset_environments
from relocation.gis import filter_patches

geoprocessing_log = logging.getLogger("geoprocessing")

def make_road_mask(tiger_lines, census_places, search_area):

	# clip tiger lines to search area
	tiger_clip = generate_gdb_filename("tiger_clip", scratch=True)

	geoprocessing_log.info("Clipping to analysis area")
	arcpy.Clip_analysis(tiger_lines, search_area, tiger_clip)

	geoprocessing_log.info("Adding and calculating roads buffer field")
	# add field to tiger lines
	field_name = "buffer_distance"
	arcpy.AddField_management(tiger_clip, field_name, "LONG")

	# calculate buffer by distances
	code_block = """def calc_distance(r_type):
		if r_type == "S1100":  # highways, or so
			return 128  # 3x cell size (30m) * sqrt(2) to capture diagonals
		elif r_type == "S1200":  # major roadways
			return 85  # 2x cell size (30m) * sqrt(2) to capture diagonals
		else:  #other
			return 43  # cell size (30m) * sqrt(2) to capture diagonals
	"""
	arcpy.CalculateField_management(tiger_clip, field_name, "calc_distance(!MTFCC!)", "PYTHON_9.3", code_block)

	# run buffer on lines
	geoprocessing_log.info("Buffering roads")
	buffered_roads = generate_gdb_filename("buffered_roads", scratch=True)
	arcpy.Buffer_analysis(tiger_clip, buffered_roads, field_name)

	# erase using census lines
	geoprocessing_log.info("Removing census places from mask (adding back to banned areas")
	road_mask = generate_gdb_filename("road_mask")
	arcpy.Erase_analysis(buffered_roads, census_places, road_mask)

	# return mask
	return road_mask


def land_use(nlcd_layer, search_area, excluded_types, tiger_lines, census_places, crs, workspace):
	arcpy.CheckOutExtension("spatial")

	geoprocessing_log.info("Extracting NLCD raster to search area")
	nlcd_in_area = arcpy.sa.ExtractByMask(nlcd_layer, search_area)
	avoid_types = [exclude.value for exclude in excluded_types]

	thresholded_raster = nlcd_in_area
	for avoid in avoid_types:  # this is inefficient, but I couldn't get it to work with a "not in" and I need something that works for n number of values
		thresholded_raster = arcpy.sa.Con(thresholded_raster != avoid, thresholded_raster, 0)

	scratch_raster = generate_gdb_filename("temp_raster", scratch=True)
	thresholded_raster.save(scratch_raster)  # save it so we can use it for environment variables

	stored_environments = store_environments(('cellSize', 'mask', 'extent', 'snapRaster'))  # cache the env vars so we can reset them at the end of this function
	arcpy.env.cellSize = scratch_raster
	arcpy.env.mask = scratch_raster
	arcpy.env.extent = scratch_raster
	arcpy.env.snapRaster = scratch_raster

	roads_mask = make_road_mask(tiger_lines, census_places=census_places, search_area=search_area)
	roads_raster = generate_gdb_filename("roads_raster")
	geoprocessing_log.info("Converting roads mask to raster")
	try:
		arcpy.PolygonToRaster_conversion(roads_mask, "OBJECTID", roads_raster)
		#arcpy.CalculateStatistics_management(roads_raster)  # crashes for invalid statistics unless we run this after the conversion
	except:
		geoprocessing_log.error("Error creating raster: {0:s} - from roads mask: {1:s}".format(roads_raster, roads_mask))
		raise

	# Raster Calculations
	final_nlcd = arcpy.sa.Con(arcpy.sa.IsNull(arcpy.sa.Raster(roads_raster)), thresholded_raster, 1)
	intermediate_raster = generate_gdb_filename("intermediate_nlcd_mask")
	projected_raster = generate_gdb_filename("projected_nlcd_mask", gdb=workspace)
	final_nlcd.save(intermediate_raster)

	reset_environments(stored_environments)

	geoprocessing_log.info("Reprojecting final raster")
	arcpy.ProjectRaster_management(intermediate_raster, projected_raster, out_coor_system=crs)

	filtered_nlcd_poly = filter_patches.convert_and_filter_by_code(projected_raster, filter_value=0)

	return filtered_nlcd_poly

