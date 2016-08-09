from django.test import TestCase
from django.http import HttpRequest
from census_search.views import place_list, place_view
import arcpy
from census_search.models import Place

'''
This is a unit test for the census_search app

To run test do: python manage.py test census_search

'''

# First features in the geodatabase
first_city = "Columbus"
first_state = "IL"
first_key = "8063"

class CensusSearchTest(TestCase):


	# Adds only one object to the database for each test. Also tests load places on first city
	def setUp(self):
		print("\nLoading first feature into test database...")

		rows = arcpy.SearchCursor(
			"C:\\Users\\Lawrence\\Documents\\ArcGIS\\Projects\\census_search\\census_search.gdb\\city_states_joined",
			fields="OBJECTID; NAME; STATENAME")

		# Get first row from the cursor
		rowlist = list(rows)
		row = rowlist[0]
		p1 = Place()
		p1.key = row.getValue("OBJECTID")
		p1.city = row.getValue("NAME")
		p1.state = row.getValue("STATENAME")

		global first_city, first_state, first_key
		first_city = p1.city
		first_state = p1.state
		first_key = p1.key

		print("First feature: " + "ID:" + str(first_key) + " " + first_city + " " + first_state)

		filename = "city_" + str(first_key)
		layer = "C:\\Users\\Lawrence\\PycharmProjects\\suitability-analysis\\census_search\\static\\geojson\\layers\\SBA city_states\\SBA.gdb\\" + filename

		p1.layer = layer
		p1.geojson = "census_search/geojson/{0:s}/{1:d}.geojson".format(p1.static_folder, p1.key)  # Use this if do not want to recreate geojson files
		# p1.as_geojson()  # create the gsojson file and set the attribute for its location
		p1.save()

		objs = Place.objects.all()
		self.assertEqual(len(objs), 1)
		print("Done.")


	# test http://127.0.0.1:8000/search/view/ for first city and first state
	def test_single_view(self):

		print("\nTesting view of first feature...")
		request = HttpRequest()
		response = place_view(request, first_city, first_state)
		self.assertTrue(response.content.startswith(b'\n\n<html>'))
		self.assertIn(b'var layer = new L.geoJson.ajax("/static/census_search/geojson/cities/' + str.encode(str(first_key)) + b".geojson", response.content)  # check contents
		print(first_city + ", " + first_state + " geojson file found")
		self.assertTrue(response.content.endswith(b'</html>'))
		print("SUCCESS.\n")


	# test http://127.0.0.1:8000/search/
	def test_search_page(self):

		print("\nTesting search view...")
		request = HttpRequest()
		response = place_list(request)
		self.assertTrue(response.content.startswith(b'\n\n<html>'))
		self.assertIn(b'<div class="ui-widget col-md-5">', response.content) #check contents
		self.assertTrue(response.content.endswith(b'</html>'))
		print("SUCCESS\n")
