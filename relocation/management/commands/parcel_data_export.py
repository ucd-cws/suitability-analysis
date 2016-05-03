__author__ = 'dsx'

import os
import csv

from django.core.management.base import BaseCommand, CommandError

from relocation.gis import conversion

from relocation.models import SuitabilityAnalysis, Location, Region, RelocatedTown

from FloodMitigation.settings import BASE_DIR

class Command(BaseCommand):
	"""
		Management command that sets up an analysis and constraints for us for testing. Created as management command
		instead of as fixtures because database changes are frequent enough right now that fixtures are quickly obsolete.
		Maybe that's just because I don't have a good enough hang of migrations yet though.
	"""

	def handle(self, *args, **options):
		run_analysis()

		self.stdout.write('Initial data loaded')


def run_analysis():

	pass
	# collect all relocated town data into one list of dicts, then export to CSV

