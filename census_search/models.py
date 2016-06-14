from django.db import models

class Place(models.Model):
	key = models.IntegerField
	city = models.CharField(max_length=100)
	state = models.CharField(max_length=2)
	geojson = models.CharField(max_length=256)


	def __str__(self):
		return self.city

	def as_geojson(self):
		#create all geojson files for each city
		self.geojson = "relocation\\static\\relocation\\geojson\\parcels\\1.geojson"
		'''
		geodatabase, layer_name = os.path.split(self.layer)
		try:
			geojson_folder = os.path.join(BASE_DIR, "relocation", "static", "relocation", "geojson", self.static_folder)
			self.geojson = "relocation/geojson/{0:s}/{1:d}.geojson".format(self.static_folder, self.id)
			if not os.path.exists(geojson_folder):  # if the folder doesn't already exist
				os.makedirs(geojson_folder)  # make it

			output_file = os.path.join(geojson_folder,
									   "{0:d}.geojson".format(self.id))  # set the full name of the output file
			geojson.file_gdb_layer_to_geojson(geodatabase, layer_name, output_file)  # run the convert
			self.save()
		except:
			if DEBUG:
				geoprocessing_log.error("Unable to convert parcels layer to geojson")
			# disabling temporarily - working on calibration - this isn't important to me right now!
			# six.reraise(*sys.exc_info())
			else:
				geoprocessing_log.error("Unable to convert parcels layer to geojson")
				'''