__author__ = 'dsx'

from django.core.management.base import BaseCommand, CommandError

from relocation import models

from relocation.gis.temp import generate_gdb_filename
import arcpy

import logging

processing_log = logging.getLogger("processing_log")
geoprocessing_log = logging.getLogger("geoprocessing")

class Command(BaseCommand):
	"""
		Management command for whatever code I want to test right now
	"""

	def handle(self, *args, **options):
		relocated = models.RelocatedTown()
