import os
import csv
import logging
import six
import sys

import numpy

from FloodMitigation.settings import BASE_DIR
from relocation.models import Region, RelocatedTown
from relocation.gis import conversion

from relocation.regression import random_forests

processing_log = logging.getLogger("processing_log")

def load_regions(region_names=None):
	regions_csv_file = os.path.join(BASE_DIR, "regions", "region_load.csv")

	with open(regions_csv_file, 'r') as csv_open:
		csv_records = csv.DictReader(csv_open)

		for record in csv_records:
			if not record["name"]:  # basically, if we're at the end, on a blank line
				continue

			if region_names and not record["name"] in region_names:  # allows us to run this and specify a name of the town to load in order to go one by one
				continue

			processing_log.info("Loading New Region: {0:s}".format(record["name"]))
			region = Region()
			for key in record.keys():
				record[key] = record[key].replace("{{BASE_DIR}}", BASE_DIR)  # replace the base directory in the paths
			try:
				region.make(**record)  # pass the record in to "make" as kwargs
			except:
				region.delete()  # if we have an exception, delete the region object in the database to reduce clutter
				six.reraise(*sys.exc_info())

def load_towns(town_names=None):
	relocation_csv_file = os.path.join(BASE_DIR, "regions", "relocated_town_load.csv")
	with open(relocation_csv_file, 'r') as csv_open:
		csv_records = csv.DictReader(csv_open)

		for record in csv_records:
			if not record["name"]:  # basically, if we're at the end, on a blank line
				continue

			if town_names and not record["name"] in town_names:  # allows us to run this and specify a name of the town to load in order to go one by one
				processing_log.debug("Skipping town {0:s}".format(record["name"]))
				continue

			processing_log.info("Loading New Town: {0:s}".format(record["name"]))
			town = RelocatedTown()
			region = Region.objects.get(short_name=record["region_short_name"])  # get the region object

			for key in record.keys():
				record[key] = record[key].replace("{{BASE_DIR}}", BASE_DIR)  # replace the base directory in the paths

			try:
				town.relocation_setup(record["name"], record["short_name"], record["before_structures"],
									  record["moved_structures"], region, make_boundaries_from_structures=True)
				town.save()

				town.process_for_calibration()

			except:
				town.delete()  # if we have an exception, delete the town object in the database to reduce clutter
				six.reraise(*sys.exc_info())

def load_and_run(regions=True, towns=True):
	if regions:
		load_regions()

	if towns:
		load_towns()

	data = get_relocation_information_as_ndarray()
	random_forests.run_and_validate(data=data, withhold=10000)


def run_model():
	data = get_relocation_information_as_ndarray()
	random_forests.run_and_validate(data=data, withhold=10000)


def export_relocation_information(include_fields=("stat_centroid_elevation",
												  "stat_centroid_distance_to_original_boundary",
												  "stat_min_elevation",
												  "stat_max_elevation",
												  "stat_mean_elevation",
												  "stat_min_slope",
												  "stat_max_slope",
												  "stat_mean_slope",
												  "stat_min_road_distance",
												  "stat_max_road_distance",
												  "stat_mean_road_distance",
												  "stat_mean_distance_to_floodplain",
												  "stat_min_distance_to_floodplain",
												  "stat_max_distance_to_floodplain",
												  "stat_min_protected_distance",
												  "stat_max_protected_distance",
												  "stat_mean_protected_distance",
												  "stat_is_protected",
												  "chosen",
												  )
								  ):
	"""
		If all of the towns are processed, then this exports it all to a single csv
	"""

	all_records = []
	for town in RelocatedTown.objects.all():
		processing_log.info("Loading town {0:s}".format(town.name))
		all_records += conversion.features_to_dict_or_array(town.parcels.layer, include_fields=include_fields)

	with open(r"C:\Users\dsx.AD3\Code\FloodMitigation\relocation\calibration\output_data.csv", 'w',) as write_file:
		csv_writer = csv.DictWriter(write_file, fieldnames=include_fields, lineterminator='\n',)  # needs the lineterminator option or else it writes an extra newline on Python 3
		csv_writer.writeheader()
		csv_writer.writerows(all_records)

	return all_records

def get_relocation_information_as_ndarray(include_fields=("stat_centroid_elevation",
																  "stat_centroid_distance_to_original_boundary",
																  "stat_min_elevation",
																  "stat_max_elevation",
																  "stat_mean_elevation",
																  "stat_min_slope",
																  "stat_max_slope",
																  "stat_mean_slope",
																  "stat_mean_distance_to_floodplain",
																  "stat_min_distance_to_floodplain",
																  "stat_max_distance_to_floodplain",
																  "chosen",
																  )
												  ):

	data_records = []

	for town in RelocatedTown.objects.all():
		processing_log.info("Loading town {0:s}".format(town.name))
		new_data = conversion.features_to_dict_or_array(town.parcels.layer, include_fields=include_fields, array=True)
		data_records += new_data

	ndarray_data_records = numpy.asarray(data_records)

	return ndarray_data_records
