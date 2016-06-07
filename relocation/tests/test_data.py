import logging

import numpy
import arcpy

from django.test import TestCase
from relocation import models
from relocation.gis import validation
from relocation.gis import geometry
from relocation.management import load
from relocation.regression import random_forests

processing_log = logging.getLogger("processing_log")

class DataTest(TestCase):
	def setUp(self):
		self.records = load.export_relocation_information()

	def test_data_in_bounds(self):
		self.assertFalse(validation.validate_bounds(self.records))

class StudyAreaTest(TestCase):
	"""
		Checks the data to make sure that each region uses roughly the same amount of data to not skew the analysis
		the no_assert args are so that these can be run outside the test runner (need to remember how to make django
		copy the DB data)
	"""
	def test_number_parcels(self, no_assert=False):
		processing_log.info("Checking number of parcels in each region")
		max_difference = .1
		total_parcels = []

		for region in models.Region.objects.all():
			num_parcels = arcpy.GetCount_management(region.parcels).getOutput(0)
			processing_log.info("Number of parcels in {} region: {}".format(region.name, num_parcels))
			total_parcels.append(int(num_parcels))


		percent_diff = (max(total_parcels) - min(total_parcels))/max(total_parcels)

		if no_assert:
			return total_parcels
		else:
			self.assertLess(percent_diff, max_difference)

	def test_DEM_area(self, no_assert=False):
		"""
			Accounts for different cellsizes, but not different projections
		:return:
		"""

		processing_log.info("Checking study area sizes")
		max_difference = .1
		total_areas = []

		for region in models.Region.objects.all():
			processing_log.info("Calculating Region {}".format(region.name))
			total_area = self.get_raster_non_null_area(region.dem)
			processing_log.info("Total usable area of {} is {}".format(region.name, total_area))
			total_areas.append(total_area)

		percent_diff = (max(total_areas) - min(total_areas))/max(total_areas)

		if no_assert:
			return total_areas
		else:
			self.assertLess(percent_diff, max_difference)

	def get_raster_non_null_area(self, raster):
		desc = arcpy.Describe(raster)
		arcpy.CheckOutExtension("Spatial")
		try:
			dem = arcpy.sa.Raster(raster)
			np_dem = arcpy.RasterToNumPyArray(dem)

			total_cells = numpy.count_nonzero(np_dem)  # get all valid cells (cells that are truly zero are problems, but right now we aren't using any
			total_area = total_cells * desc.meanCellWidth * desc.meanCellHeight
		finally:
			arcpy.CheckInExtension("Spatial")

		return total_area

class ModelTest(TestCase):
	def setUp(self):
		self.records = load.get_relocation_information_as_ndarray()

	def OFFLINE_test_model_true_correct(self):
		"""
		Incomplete
		:return:
		"""
		model, x_validate, y_validate, percent_incorrect_y = random_forests.run_and_validate(self.records)


class TownTest(TestCase):
	def setUp(self):
		self.towns = models.RelocatedTown.objects.all()

	def test_town_boundary_overlap(self,  max_overlap=5):
		"""
			Tests that the old and new town boundaries don't overlap too much and warns if they do
		:return:
		"""

		self.setUp()

		failure = False

		for town in self.towns:
			processing_log.info("Testing percent overlap for {}".format(town.name))
			results = geometry.percent_overlap(town.before_location.boundary_polygon, town.moved_location.boundary_polygon, dissolve=False)
			processing_log.info("Overlap is {}".format(results["percent_overlap"]))
			try:
				self.assertLess(results["percent_overlap"], max_overlap)
			except:
				failure = True

		if failure:
			raise AssertionError("Some towns failed - see full output for details")

