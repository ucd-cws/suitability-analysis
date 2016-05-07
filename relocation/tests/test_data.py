import logging

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

