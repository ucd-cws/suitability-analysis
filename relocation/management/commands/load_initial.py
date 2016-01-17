__author__ = 'dsx'

from django.core.management.base import BaseCommand, CommandError

from relocation.models import SuitabilityAnalysis, Location, Region
from relocation import models


class Command(BaseCommand):
	"""
		Management command that sets up an analysis and constraints for us for testing. Created as management command
		instead of as fixtures because database changes are frequent enough right now that fixtures are quickly obsolete.
		Maybe that's just because I don't have a good enough hang of migrations yet though.
	"""

	def handle(self, *args, **options):
		load_initial_data()

		self.stdout.write('Initial data loaded')


def load_initial_data():
	region = Region()
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
	region.setup()
	region.save()

	location = Location()
	location.name = "Test Valmeyer Move"
	location.short_name = "test_valmeyer_1"
	location.region = region
	location.working_directory = r"C:\Users\dsx.AD3\Code\FloodMitigation\locations\Valmeyer_Full"
	location.layers = r"C:\Users\dsx.AD3\Code\FloodMitigation\locations\Valmeyer_Full\Valmeyer_Full.gdb"
	location.boundary_polygon_name = "valmeyer_full"
	location.search_distance = 12000
	location.save()  # location setup occurs after suitability analysis is created

	suitable = SuitabilityAnalysis()
	suitable.name = "Valmeyer Full - Includes modern area"
	suitable.short_name = "valmeyer_full"
	suitable.working_directory = r"C:\Users\dsx.AD3\Code\FloodMitigation\geospatial_analysis\southernillinois"
	suitable.workspace = r"C:\Users\dsx.AD3\Code\FloodMitigation\geospatial_analysis\southernillinois\layers.gdb"
	suitable.location = location
	suitable.save()
	suitable.setup()
	suitable.save()

	location.setup()
	location.save()

	census_constraint = models.CensusPlacesConstraint()
	census_constraint.name = "TestCensusConstraint"
	census_constraint.description = "test"
	census_constraint.suitability_analysis = suitable
	census_constraint.save()

	slope_constraint = models.LocalSlopeConstraint()
	slope_constraint.name = "TestSlopeConstraint"
	slope_constraint.description = "test"
	slope_constraint.suitability_analysis = suitable
	slope_constraint.max_slope = 5
	slope_constraint.save()

	excluded_types = []
	for choice in (11, 12, 22, 23, 24):
		new_choice_obj = models.LandCoverChoice()
		new_choice_obj.value = choice
		new_choice_obj.save()
		excluded_types.append(new_choice_obj)

	land_cover_constraint = models.LandCoverConstraint()
	land_cover_constraint.name = "TestLandCoverConstraint"
	land_cover_constraint.description = "test"
	land_cover_constraint.suitability_analysis = suitable
	land_cover_constraint.save()
	land_cover_constraint.excluded_types = excluded_types  # perennial ice/snow, urban types
	land_cover_constraint.save()

	protected_areas_constraint = models.ProtectedAreasConstraint()
	protected_areas_constraint.name = "TestProtectedAreasConstraint"
	protected_areas_constraint.description = "test"
	protected_areas_constraint.suitability_analysis = suitable
	protected_areas_constraint.save()

	floodplain_constraint = models.FloodplainAreasConstraint()
	floodplain_constraint.name = "TestFloodplainConstraint"
	floodplain_constraint.description = "test"
	floodplain_constraint.suitability_analysis = suitable
	floodplain_constraint.save()

	roads_constraint = models.RoadClassDistanceConstraintManager()
	roads_constraint.name = "TestRoadsContraint"
	roads_constraint.description = "test"
	roads_constraint.suitability_analysis = suitable
	roads_constraint.save()

	first_roads_constraint = models.RoadClassDistanceConstraint()
	first_roads_constraint.name = "TestRoadConstraint1"
	first_roads_constraint.description = "test"
	first_roads_constraint.constraint_manager = roads_constraint
	first_roads_constraint.max_distance = "10000"
	first_roads_constraint.where_clause = "MTFCC = \"S1100\""  # road type is highway
	first_roads_constraint.save()

	second_roads_constraint = models.RoadClassDistanceConstraint()
	second_roads_constraint.name = "TestRoadConstraint2"
	second_roads_constraint.description = "test"
	second_roads_constraint.constraint_manager = roads_constraint
	second_roads_constraint.max_distance = "1000"
	second_roads_constraint.where_clause = ""  # any road and testing a blank where clause
	second_roads_constraint.save()

