__author__ = 'dsx'

from django.core.management.base import BaseCommand, CommandError

from relocation import models


class Command(BaseCommand):
	"""
		Management command that sets up an analysis and constraints for us for testing. Created as management command
		instead of as fixtures because database changes are frequent enough right now that fixtures are quickly obsolete.
		Maybe that's just because I don't have a good enough hang of migrations yet though.
	"""

	def add_arguments(self, parser):
		parser.add_argument('suitability_analysis', nargs='+', tpye=str)

	def handle(self, *args, **options):
		suitability_analysis = models.SuitabilityAnalysis.objects.get(name=options["suitability_analysis"])
		suitability_analysis.location.parcels.process_parcels()

		self.stdout.write('Parcels processed')

