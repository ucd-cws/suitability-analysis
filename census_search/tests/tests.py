from django.core.urlresolvers import resolve
from django.test import TestCase
from django.http import HttpRequest
from census_search.views import place_list, place_view

from selenium import webdriver
import arcpy
from census_search.models import Place



# assert 'Search test' in browser.title, "Browser title was " + browser.title

class CensusSearchTest(TestCase):

	# test load places on (current) first city, Cudahy, WI. Also places it in the test DB, "default"
	def test_load_places(self):
		print("Testing load_places for first feature")

		rows = arcpy.SearchCursor(
			"C:\\Users\\Lawrence\\Documents\\ArcGIS\\Projects\\census_search\\census_search.gdb\\city_states_joined",
			fields="OBJECTID; NAME; STATENAME")

		# Iterate through the rows in the cursor
		rowlist = list(rows)
		row = rowlist[0]
		p1 = Place()
		p1.key = row.getValue("OBJECTID")
		p1.city = row.getValue("NAME")
		p1.state = row.getValue("STATENAME")

		filename = "city_" + str(p1.key)
		layer = "C:\\Users\\Lawrence\\PycharmProjects\\suitability-analysis\\census_search\\static\\geojson\\layers\\SBA city_states\\SBA.gdb\\" + filename

		p1.layer = layer
		# p1.geojson = "census_search/geojson/{0:s}/{1:d}.geojson".format(p1.static_folder, p1.key)  # Use this if do not want to recreate geojson files
		#p1.as_geojson()  # create the gsojson file and set the attribute for its location
		p1.save()


		print("Done.")

	def test_search_page(self):
		request = HttpRequest()
		response = place_list(request)
		self.assertTrue(response.content.startswith(b'\n\n<html>'))
		self.assertIn(b'<div class="ui-widget col-md-5">', response.content) #check contents
		self.assertTrue(response.content.endswith(b'</html>'))

	def test_view_page(self):
		request = HttpRequest()
		response = place_view(request, "Cudahy", "WI")
		self.assertTrue(response.content.startswith(b'\n\n<html>'))
		self.assertIn(b'var layer = new L.geoJson.ajax("/static/census_search/geojson/cities/1.geojson").addTo(object_map);', response.content)  # check contents
		self.assertTrue(response.content.endswith(b'</html>'))



# test view for Cudahy, WI in city list view

# test view for (current) first city, Cudahy, WI
# http://127.0.0.1:8000/search/view/WI/Cudahy/