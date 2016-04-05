import os
import csv
import logging

from FloodMitigation.settings import BASE_DIR
from relocation.models import Region, RelocatedTown
from relocation.gis import conversion

processing_log = logging.getLogger("processing_log")

def load_regions(region_name=None):
	regions_csv_file = os.path.join(BASE_DIR, "regions", "region_load.csv")

	with open(regions_csv_file, 'r') as csv_open:
		csv_records = csv.DictReader(csv_open)

		for record in csv_records:
			if not record["name"]:  # basically, if we're at the end, on a blank line
				continue

			if region_name and not record["name"] == region_name:  # allows us to run this and specify a name of the town to load in order to go one by one
				continue

			processing_log.info("Loading New Region: {0:s}".format(record["name"]))
			region = Region()
			for key in record.keys():
				record[key] = record[key].replace("{{BASE_DIR}}", BASE_DIR)  # replace the base directory in the paths
			region.make(**record)  # pass the record in to "make" as kwargs


def load_towns(town_name=None):
	relocation_csv_file = os.path.join(BASE_DIR, "regions", "relocated_town_load.csv")
	with open(relocation_csv_file, 'r') as csv_open:
		csv_records = csv.DictReader(csv_open)

		for record in csv_records:
			if not record["name"]:  # basically, if we're at the end, on a blank line
				continue

			if town_name and not record["name"] == town_name:  # allows us to run this and specify a name of the town to load in order to go one by one
				continue

			processing_log.info("Loading New Town: {0:s}".format(record["name"]))
			town = RelocatedTown()
			region = Region.objects.get(short_name=record["region_short_name"])  # get the region object

			for key in record.keys():
				record[key] = record[key].replace("{{BASE_DIR}}", BASE_DIR)  # replace the base directory in the paths

			town.relocation_setup(record["name"], record["short_name"], record["before_structures"],
								  record["moved_structures"], region, make_boundaries_from_structures=True)
			town.save()

			town.process_for_calibration()


def export_relocation_information(include_fields=("stat_centroid_elevation",
												  "stat_centroid_distance",
												  "stat_min_elevation",
												  "stat_max_elevation",
												  "stat_mean_elevation",
												  "stat_min_slope",
												  "stat_max_slope",
												  "stat_mean_slope",
												  "stat_mean_distance_to_floodplain",
												  "stat_min_distance_to_floodplain",
												  "stat_max_distance_to_floodplain",
												  "stat_centroid_elevation",
												  "chosen",
												  )
								  ):
	"""
		If all of the towns are processed, then this exports it all to a single csv
	"""

	all_records = []
	for town in RelocatedTown.objects.all():
		if not town.active:  # if town is deactivated
			continue

		all_records += conversion.features_to_dict(town.parcels.layer, include_fields=include_fields)

		with open(r"C:\Users\dsx.AD3\Code\FloodMitigation\relocation\calibration\output_data.csv", 'w') as write_file:
			csv_writer = csv.DictWriter(write_file, fieldnames=include_fields)
			csv_writer.writerows(all_records)
