import logging

from django.test import TestCase
from relocation import models

processing_log = logging.getLogger("processing_log")

class RegionTest(TestCase):
	def test_create_region(self):

		processing_log.info("Creating Region")

		region = models.Region()
		region.name = "Southern Illinois"
		region.short_name = "southernillinois"
		region.crs_string = 'PROJCS["NAD_1983_Contiguous_USA_Albers",GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Albers"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-96.0],PARAMETER["Standard_Parallel_1",29.5],PARAMETER["Standard_Parallel_2",45.5],PARAMETER["Latitude_Of_Origin",23.0],UNIT["Meter",1.0]]'
		region.base_directory = r"C:\Users\dsx.AD3\Code\FloodMitigation\regions\SouthernIllinois"
		region.layers = r"C:\Users\dsx.AD3\Code\FloodMitigation\regions\SouthernIllinois\layers.gdb"
		region.dem_name = "Flood_dem_10m_albers"
		region.slope_name = "flood_slope_degree_albers"
		region.nlcd_name = "nlcd_2011_land_cover"
		region.census_places_name = "census_places_2015"
		region.protected_areas_name = "protected_areas_2015"
		region.floodplain_areas_name = "IL_unprotected_floodplain_2012"
		region.tiger_lines_name = "tiger_roads_2011_albers"
		region.parcels_name = "monroe_parcels"
		region.save()

		processing_log.info("Running Regions Setup")
		region.setup()
		region.save()


class RelocationTest(TestCase):
	def test_create_relocation_town(self):
		processing_log.info("Creating Relocation Town")

		region = models.Region()
		region.name = "Southern Illinois"
		region.short_name = "southernillinois"
		region.crs_string = 'PROJCS["NAD_1983_Contiguous_USA_Albers",GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Albers"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-96.0],PARAMETER["Standard_Parallel_1",29.5],PARAMETER["Standard_Parallel_2",45.5],PARAMETER["Latitude_Of_Origin",23.0],UNIT["Meter",1.0]]'
		region.base_directory = r"C:\Users\dsx.AD3\Code\FloodMitigation\regions"
		region.layers = r"C:\Users\dsx.AD3\Code\FloodMitigation\regions\calibration_data.gdb"
		region.dem = r"C:\Users\dsx.AD3\Code\FloodMitigation\regions\calibration_data.gdb\Valmeyer_DEM_UTM"
		region.slope = r"C:\Users\dsx.AD3\Code\FloodMitigation\regions\calibration_data.gdb\Valmeyer_slope"
		region.nlcd = r"C:\Users\dsx.AD3\Code\FloodMitigation\regions\national.gdb\nlcd_2011"
		region.census_places = r"C:\Users\dsx.AD3\Code\FloodMitigation\regions\national.gdb\census_places\cb_2014_IL_place_500k"
		region.floodplain_areas = r"C:\Users\dsx.AD3\Code\FloodMitigation\regions\national.gdb\simple_levee_protection"
		region.parcels = r"C:\Users\dsx.AD3\Code\FloodMitigation\regions\SouthernIllinois\layers.gdb\monroe_parcels"
		region.save()
		region.setup(process_paths_from_name=False)
		region.save()

		relocated = models.RelocatedTown()
		relocated.relocation_setup("Valmeyer", "valmeyer", r"C:\Users\dsx.AD3\Code\FloodMitigation\regions\calibration_data.gdb\Valmeyer_IL_Structures_Old", r"C:\Users\dsx.AD3\Code\FloodMitigation\regions\calibration_data.gdb\Valmeyer_IL_Structures", region, True)
		relocated.save()



