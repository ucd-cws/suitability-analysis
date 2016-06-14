from django.db import models
from FloodMitigation.settings import BASE_DIR, DEBUG
from relocation.gis import geojson
import os, logging, six, sys
geoprocessing_log = logging.getLogger("geoprocessing_log")

class Place(models.Model):
	key = models.IntegerField()
	city = models.CharField(max_length=100)
	state = models.CharField(max_length=2)
	geojson = models.CharField(max_length=256)
	layer = models.CharField(max_length=256)
	static_folder = "cities"


	def __str__(self):
		return self.city

	def as_geojson(self):
		#create geojson files for each city
		#self.geojson = "census_search\\static\\census_search\\geojson\\cities\\1.geojson"

		geodatabase, layer_name = os.path.split(self.layer)
		try:
			geojson_folder = os.path.join(BASE_DIR, "census_search", "static", "census_search", "geojson", self.static_folder) # folder location
			self.geojson = "census_search/geojson/{0:s}/{1:d}.geojson".format(self.static_folder, self.key) # update geojson attribute
			if not os.path.exists(geojson_folder):  # if the folder doesn't already exist
				os.makedirs(geojson_folder)  # make it

			output_file = os.path.join(geojson_folder,
									   "{0:d}.geojson".format(self.key))  # set the full name of the output file
			geojson.file_gdb_layer_to_geojson(geodatabase, layer_name, output_file)  # run the convert
			self.save()
		except:
			if DEBUG:
				geoprocessing_log.error("Unable to convert parcels layer to geojson")
				# disabling temporarily - working on calibration - this isn't important to me right now!
				six.reraise(*sys.exc_info())
			else:
				geoprocessing_log.error("Unable to convert parcels layer to geojson")
