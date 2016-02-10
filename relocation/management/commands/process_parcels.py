__author__ = 'dsx'

from django.core.management.base import BaseCommand, CommandError

from relocation import models

from code_library.common.geospatial import generate_gdb_filename
import arcpy

import logging

processing_log = logging.getLogger("processing_log")
geoprocessing_log = logging.getLogger("geoprocessing")


class Command(BaseCommand):
	"""
		Management command that sets up an analysis and constraints for us for testing. Created as management command
		instead of as fixtures because database changes are frequent enough right now that fixtures are quickly obsolete.
		Maybe that's just because I don't have a good enough hang of migrations yet though.
	"""

	def add_arguments(self, parser):
		parser.add_argument('suitability_analysis', nargs='+', type=str)

	def handle(self, *args, **options):
		suitability_analysis = models.SuitabilityAnalysis.objects.get(pk=2)
		#temp_correction(suitability_analysis.location)
		processing_log.info("Running setup")

		suitability_analysis.parcels.setup()
		processing_log.info("Done setting up")

		self.stdout.write('Parcels processed')


def temp_correction(correction):
	"""
		A one time function to correct an object - can be deleted
	:return:
	"""
	processing_log.warning("{0:s}".format(correction.parcels.layer))
	if correction.parcels.layer is None or correction.parcels.layer == "":
		correction.parcels.layer = generate_gdb_filename(correction.region.parcels_name, gdb=correction.layers)
		processing_log.warning("{0:s}".format(correction.parcels.layer))
		arcpy.CopyFeatures_management(correction.region.parcels, correction.parcels.layer)
		correction.parcels.save()

	processing_log.warning("Done setting up")

