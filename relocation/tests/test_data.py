import logging

from django.test import TestCase
from relocation.gis import validation
from relocation.management import load
from relocation.regression import logistic

processing_log = logging.getLogger("processing_log")

class DataTest(TestCase):
	def setUp(self):
		self.records = load.export_relocation_information()

	def test_data_in_bounds(self):
		self.assertFalse(validation.validate_bounds(self.records))

class ModelTest(TestCase):
	def setUp(self):
		self.records = load.get_relocation_information_as_ndarray()

	def test_model_true_correct(self):
		model, x_validate, y_validate, percent_incorrect_y = logistic.run_and_validate(self.records)
