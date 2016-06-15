from django.core.management.base import BaseCommand, CommandError
from census_search.models import Place
import arcpy

'''
load_places function

Retrieves gdb data for city_states, which joins the STATEID to State acronyms.
Used Split By Attribute tool in ArcGIS to create the layers for each city for use in as_geojson() for file_gdb_layer_to_geojson().
This tool outputted the data to a gdb. Each layer matches each city by their unique ID.

Calls as_geojson() to create respective geojson files for each city.

'''


class Command(BaseCommand):
	help = 'Loads data to database'

	def handle(self, *args, **options):
		self.stdout.write("Loading data...")

		rows = arcpy.SearchCursor(
			"C:\\Users\\Lawrence\\Documents\\ArcGIS\\Projects\\census_search\\census_search.gdb\\city_states_joined",
			fields="OBJECTID; NAME; STATENAME")

		# Iterate through the rows in the cursor
		for row in rows:
			p1 = Place()
			p1.key = row.getValue("OBJECTID")
			p1.city = row.getValue("NAME")
			p1.state = row.getValue("STATENAME")

			filename = "city_" + str(p1.key)
			layer = "C:\\Users\\Lawrence\\PycharmProjects\\suitability-analysis\\census_search\\static\\geojson\\layers\\SBA city_states\\SBA.gdb\\" + filename

			p1.layer = layer
			#p1.geojson = "census_search/geojson/{0:s}/{1:d}.geojson".format(p1.static_folder, p1.key)  # Use this if do not want to recreate geojson files
			p1.as_geojson()  # create the gsojson file and set the attribute for its location
			p1.save()

		self.stdout.write("Done.")
