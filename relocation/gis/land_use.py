__author__ = 'dsx'

import logging

import arcpy

from code_library.common.geospatial import generate_gdb_filename

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
	arcpy.Buffer_analysis(tiger_clip,buffered_roads,field_name)

	# erase using census lines
	geoprocessing_log.info("Removing census places from mask (adding back to banned areas")
	road_mask = generate_gdb_filename("road_mask")
	arcpy.Erase_analysis(buffered_roads, census_places, road_mask)

	# return mask
	return road_mask


def land_use(nlcd_layer, search_area, tiger_lines, census_places):
	arcpy.CheckOutExtension("spatial")

	geoprocessing_log.info("Extracting NLCD raster to search area")
	nlcd_in_area = arcpy.sa.ExtractByMask(nlcd_layer, search_area)
	thresholded_raster = nlcd_in_area > 24 | nlcd_in_area == 21  # TODO: find a way to make this a parameter - an explicit list of banned values?


# Script arguments
NLCD_Land_Cover_Layer = arcpy.GetParameterAsText(0)
if NLCD_Land_Cover_Layer == '#' or not NLCD_Land_Cover_Layer:
    NLCD_Land_Cover_Layer = "X:\\Flood_Mitigation\\GIS\\Suitability_Data.gdb\\nlcd_2001_land_cover" # provide a default value if unspecified

Tiger_Lines_for_Same_Year = arcpy.GetParameterAsText(1)
if Tiger_Lines_for_Same_Year == '#' or not Tiger_Lines_for_Same_Year:
    Tiger_Lines_for_Same_Year = "tiger_roads_2011" # provide a default value if unspecified

Census_Places_for_Same_Year = arcpy.GetParameterAsText(2)
if Census_Places_for_Same_Year == '#' or not Census_Places_for_Same_Year:
    Census_Places_for_Same_Year = "X:\\Flood_Mitigation\\GIS\\exploration\\suitability_dev\\suitability.gdb\\Census_Places_1990" # provide a default value if unspecified

Output_Coordinate_System = arcpy.GetParameterAsText(3)
if Output_Coordinate_System == '#' or not Output_Coordinate_System:
    Output_Coordinate_System = "PROJCS['NAD_1983_Contiguous_USA_Albers',GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Albers'],PARAMETER['False_Easting',0.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-96.0],PARAMETER['Standard_Parallel_1',29.5],PARAMETER['Standard_Parallel_2',45.5],PARAMETER['Latitude_Of_Origin',23.0],UNIT['Meter',1.0]]" # provide a default value if unspecified

Alignment_Raster = arcpy.GetParameterAsText(4)
if Alignment_Raster == '#' or not Alignment_Raster:
    Alignment_Raster = "X:\\Flood_Mitigation\\GIS\\derived.gdb\\Flood_dem_10m_albers" # provide a default value if unspecified

# Local variables:
NLCD_Binary = NLCD_Land_Cover_Layer
Buffered_Roads_Raster = NLCD_Binary
Roads_Masked_Out = Buffered_Roads_Raster
rastercalc2_ProjectRaster = Roads_Masked_Out
Road_Mask = Census_Places_for_Same_Year
TIGER = Tiger_Lines_for_Same_Year
tl_2011_55113_roads_CopyFeat1 = TIGER
With_Buffer_Field = TIGER
tl_2011_55113_roads_CopyFeat = With_Buffer_Field

# Process: Copy Features
arcpy.CopyFeatures_management(Tiger_Lines_for_Same_Year, TIGER, "", "0", "0", "0")

# Process: Add Field
arcpy.AddField_management(TIGER, "Buffer_Distance", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

# Process: Calculate Field
arcpy.CalculateField_management(With_Buffer_Field, "Buffer_Distance", "distance( !MTFCC!)", "PYTHON_9.3", "def distance(r_type):\\n  if r_type == \"S1100\":  # highways, or so\\n    return 128  # 3x cell size (30m) * sqrt(2) to capture diagonals\\n  elif r_type == \"S1200\":  # major roadways\\n    return 85  # 2x cell size (30m) * sqrt(2) to capture diagonals\\n  else:  #other\\n    return 43  # cell size (30m) * sqrt(2) to capture diagonals")

# Process: Buffer
arcpy.Buffer_analysis(TIGER, tl_2011_55113_roads_CopyFeat1, "Buffer_Distance", "FULL", "ROUND", "NONE", "", "PLANAR")

# Process: Erase
arcpy.Erase_analysis(tl_2011_55113_roads_CopyFeat1, Census_Places_for_Same_Year, Road_Mask, "")

# Process: Filter out unbuildable types
tempEnvironment0 = arcpy.env.newPrecision
arcpy.env.newPrecision = "SINGLE"
tempEnvironment1 = arcpy.env.autoCommit
arcpy.env.autoCommit = "1000"
tempEnvironment2 = arcpy.env.XYResolution
arcpy.env.XYResolution = ""
tempEnvironment3 = arcpy.env.XYDomain
arcpy.env.XYDomain = ""
tempEnvironment4 = arcpy.env.scratchWorkspace
arcpy.env.scratchWorkspace = "E:\\Users\\dsx\\Documents\\ArcGIS\\Default.gdb"
tempEnvironment5 = arcpy.env.cartographicPartitions
arcpy.env.cartographicPartitions = ""
tempEnvironment6 = arcpy.env.terrainMemoryUsage
arcpy.env.terrainMemoryUsage = "false"
tempEnvironment7 = arcpy.env.MTolerance
arcpy.env.MTolerance = ""
tempEnvironment8 = arcpy.env.compression
arcpy.env.compression = "LZ77"
tempEnvironment9 = arcpy.env.coincidentPoints
arcpy.env.coincidentPoints = "MEAN"
tempEnvironment10 = arcpy.env.randomGenerator
arcpy.env.randomGenerator = "0 ACM599"
tempEnvironment11 = arcpy.env.outputCoordinateSystem
arcpy.env.outputCoordinateSystem = ""
tempEnvironment12 = arcpy.env.rasterStatistics
arcpy.env.rasterStatistics = "STATISTICS 1 1"
tempEnvironment13 = arcpy.env.ZDomain
arcpy.env.ZDomain = ""
tempEnvironment14 = arcpy.env.transferDomains
arcpy.env.transferDomains = "false"
tempEnvironment15 = arcpy.env.resamplingMethod
arcpy.env.resamplingMethod = "NEAREST"
tempEnvironment16 = arcpy.env.projectCompare
arcpy.env.projectCompare = "NONE"
tempEnvironment17 = arcpy.env.cartographicCoordinateSystem
arcpy.env.cartographicCoordinateSystem = "PROJCS['NAD_1983_Contiguous_USA_Albers',GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Albers'],PARAMETER['False_Easting',0.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-96.0],PARAMETER['Standard_Parallel_1',29.5],PARAMETER['Standard_Parallel_2',45.5],PARAMETER['Latitude_Of_Origin',23.0],UNIT['Meter',1.0]]"
tempEnvironment18 = arcpy.env.configKeyword
arcpy.env.configKeyword = ""
tempEnvironment19 = arcpy.env.outputZFlag
arcpy.env.outputZFlag = "Same As Input"
tempEnvironment20 = arcpy.env.qualifiedFieldNames
arcpy.env.qualifiedFieldNames = "true"
tempEnvironment21 = arcpy.env.tileSize
arcpy.env.tileSize = "128 128"
tempEnvironment22 = arcpy.env.parallelProcessingFactor
arcpy.env.parallelProcessingFactor = ""
tempEnvironment23 = arcpy.env.pyramid
arcpy.env.pyramid = "PYRAMIDS -1 NEAREST DEFAULT 75 NO_SKIP"
tempEnvironment24 = arcpy.env.referenceScale
arcpy.env.referenceScale = ""
tempEnvironment25 = arcpy.env.extent
arcpy.env.extent = "DEFAULT"
tempEnvironment26 = arcpy.env.XYTolerance
arcpy.env.XYTolerance = ""
tempEnvironment27 = arcpy.env.tinSaveVersion
arcpy.env.tinSaveVersion = "CURRENT"
tempEnvironment28 = arcpy.env.nodata
arcpy.env.nodata = "NONE"
tempEnvironment29 = arcpy.env.MDomain
arcpy.env.MDomain = ""
tempEnvironment30 = arcpy.env.spatialGrid1
arcpy.env.spatialGrid1 = "0"
tempEnvironment31 = arcpy.env.cellSize
arcpy.env.cellSize = "MAXOF"
tempEnvironment32 = arcpy.env.outputZValue
arcpy.env.outputZValue = ""
tempEnvironment33 = arcpy.env.outputMFlag
arcpy.env.outputMFlag = "Same As Input"
tempEnvironment34 = arcpy.env.geographicTransformations
arcpy.env.geographicTransformations = "NAD_1927_To_NAD_1983_NADCON"
tempEnvironment35 = arcpy.env.spatialGrid2
arcpy.env.spatialGrid2 = "0"
tempEnvironment36 = arcpy.env.ZResolution
arcpy.env.ZResolution = ""
tempEnvironment37 = arcpy.env.mask
arcpy.env.mask = ""
tempEnvironment38 = arcpy.env.spatialGrid3
arcpy.env.spatialGrid3 = "0"
tempEnvironment39 = arcpy.env.maintainSpatialIndex
arcpy.env.maintainSpatialIndex = "false"
tempEnvironment40 = arcpy.env.workspace
arcpy.env.workspace = "E:\\Users\\dsx\\Documents\\ArcGIS\\Default.gdb"
tempEnvironment41 = arcpy.env.MResolution
arcpy.env.MResolution = ""
tempEnvironment42 = arcpy.env.derivedPrecision
arcpy.env.derivedPrecision = "HIGHEST"
tempEnvironment43 = arcpy.env.ZTolerance
arcpy.env.ZTolerance = ""
arcpy.gp.RasterCalculator_sa("(\"%NLCD Land Cover Layer%\" > 24)  |  (\"%NLCD Land Cover Layer%\" == 21)", NLCD_Binary)
arcpy.env.newPrecision = tempEnvironment0
arcpy.env.autoCommit = tempEnvironment1
arcpy.env.XYResolution = tempEnvironment2
arcpy.env.XYDomain = tempEnvironment3
arcpy.env.scratchWorkspace = tempEnvironment4
arcpy.env.cartographicPartitions = tempEnvironment5
arcpy.env.terrainMemoryUsage = tempEnvironment6
arcpy.env.MTolerance = tempEnvironment7
arcpy.env.compression = tempEnvironment8
arcpy.env.coincidentPoints = tempEnvironment9
arcpy.env.randomGenerator = tempEnvironment10
arcpy.env.outputCoordinateSystem = tempEnvironment11
arcpy.env.rasterStatistics = tempEnvironment12
arcpy.env.ZDomain = tempEnvironment13
arcpy.env.transferDomains = tempEnvironment14
arcpy.env.resamplingMethod = tempEnvironment15
arcpy.env.projectCompare = tempEnvironment16
arcpy.env.cartographicCoordinateSystem = tempEnvironment17
arcpy.env.configKeyword = tempEnvironment18
arcpy.env.outputZFlag = tempEnvironment19
arcpy.env.qualifiedFieldNames = tempEnvironment20
arcpy.env.tileSize = tempEnvironment21
arcpy.env.parallelProcessingFactor = tempEnvironment22
arcpy.env.pyramid = tempEnvironment23
arcpy.env.referenceScale = tempEnvironment24
arcpy.env.extent = tempEnvironment25
arcpy.env.XYTolerance = tempEnvironment26
arcpy.env.tinSaveVersion = tempEnvironment27
arcpy.env.nodata = tempEnvironment28
arcpy.env.MDomain = tempEnvironment29
arcpy.env.spatialGrid1 = tempEnvironment30
arcpy.env.cellSize = tempEnvironment31
arcpy.env.outputZValue = tempEnvironment32
arcpy.env.outputMFlag = tempEnvironment33
arcpy.env.geographicTransformations = tempEnvironment34
arcpy.env.spatialGrid2 = tempEnvironment35
arcpy.env.ZResolution = tempEnvironment36
arcpy.env.mask = tempEnvironment37
arcpy.env.spatialGrid3 = tempEnvironment38
arcpy.env.maintainSpatialIndex = tempEnvironment39
arcpy.env.workspace = tempEnvironment40
arcpy.env.MResolution = tempEnvironment41
arcpy.env.derivedPrecision = tempEnvironment42
arcpy.env.ZTolerance = tempEnvironment43

# Process: Polygon to Raster
tempEnvironment0 = arcpy.env.snapRaster
arcpy.env.snapRaster = "E:\\Users\\dsx\\Documents\\ArcGIS\\Default.gdb\\rastercalc1"
tempEnvironment1 = arcpy.env.extent
arcpy.env.extent = "E:\\Users\\dsx\\Documents\\ArcGIS\\Default.gdb\\rastercalc1"
tempEnvironment2 = arcpy.env.cellSize
arcpy.env.cellSize = "E:\\Users\\dsx\\Documents\\ArcGIS\\Default.gdb\\rastercalc1"
arcpy.PolygonToRaster_conversion(Road_Mask, "OBJECTID", Buffered_Roads_Raster, "CELL_CENTER", "NONE", NLCD_Binary)
arcpy.env.snapRaster = tempEnvironment0
arcpy.env.extent = tempEnvironment1
arcpy.env.cellSize = tempEnvironment2

# Process: Raster Calculator
arcpy.gp.RasterCalculator_sa("Con(IsNull(\"%Buffered_Roads_Raster%\"),\"%NLCD Binary%\", 1)", Roads_Masked_Out)

# Process: Project Raster
tempEnvironment0 = arcpy.env.snapRaster
arcpy.env.snapRaster = "X:\\Flood_Mitigation\\GIS\\derived.gdb\\Flood_dem_10m_albers"
tempEnvironment1 = arcpy.env.cellSize
arcpy.env.cellSize = "X:\\Flood_Mitigation\\GIS\\derived.gdb\\Flood_dem_10m_albers"
tempEnvironment2 = arcpy.env.mask
arcpy.env.mask = "X:\\Flood_Mitigation\\GIS\\derived.gdb\\Flood_dem_10m_albers"
arcpy.ProjectRaster_management(Roads_Masked_Out, rastercalc2_ProjectRaster, Output_Coordinate_System, "NEAREST", Alignment_Raster, "", "", "GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]]")
arcpy.env.snapRaster = tempEnvironment0
arcpy.env.cellSize = tempEnvironment1
arcpy.env.mask = tempEnvironment2

