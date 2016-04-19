import logging

import numpy as np

from relocation.management import load
from relocation.regression import random_forests

processing_log = logging.getLogger("processing_log")
file_log = logging.getLogger("silent_error_log")

# large negative values reflect that when subtracting the original value out of the new location value, we can get large negative numbers.
# this is just a broad measure. A better one would be based on each parcel.
# The distance to roads can't be more negative than the original boundary's distance to roads + the centroid distance (plus maybe a fudge factor), for example
# Right now, I just want to flag absurdly large and invalid values. We'll add more validation later
meters_degrees_valid_values_min_max = {"stat_centroid_elevation": (-9000,9000),
					  "stat_centroid_distance_to_original_boundary": (0,100000),
					  "stat_min_elevation": (-9000,9000),
					  "stat_max_elevation": (-9000,9000),
					  "stat_mean_elevation": (-9000,9000),
					  "stat_min_slope": (-90,90),
					  "stat_max_slope": (-90,90),
					  "stat_mean_slope": (-90,90),
					  "stat_min_road_distance": (-100000,100000),
					  "stat_max_road_distance": (-100000,100000),
					  "stat_mean_road_distance": (-100000,100000),
					  "stat_mean_distance_to_floodplain": (-100000,100000),
					  "stat_min_distance_to_floodplain": (-100000,100000),
					  "stat_max_distance_to_floodplain": (-100000,100000),
					  "stat_min_protected_distance": (-100000,100000),
					  "stat_max_protected_distance": (-100000,100000),
					  "stat_mean_protected_distance": (-100000,100000),
					  "stat_is_protected": (0,1),
					  "chosen": (0,1),
}

def validate_bounds(data_dict_list, valid_values=meters_degrees_valid_values_min_max):
	"""

	:param data_dict_list:
	:param valid_values:
	:return: bool: False if no bounds errors, True if there are
	"""

	had_errors = False
	for record in data_dict_list:
		for key in record.keys():
			if not record[key] >= valid_values[key][0] or not record[key] <= valid_values[key][1]:
				had_errors = True
				file_log.error("Value {} is out of bounds for field {}".format(record[key], key))

	return had_errors


def test_withholding(num_runs=3):
	model = random_forests.ModelRunner()
	model.load_data()
	for withhold in range(1, 51):
		withholding = withhold / 100  # range only works with ints, so this is a chap hack to get it to give me floats - probably less accurate than making my own stepper...
		processing_log.info("Withholding Value at {}".format(withholding))
		error_values = []
		for run_num in range(num_runs):
			processing_log.info('Run {}'.format(run_num))
			model.run_and_validate(withhold=withholding)
			error_values.append(model.percent_incorrect)

		error_array = np.asarray(error_values)
		if num_runs > 2:
			std = error_array.std()
		else:
			std = None

		file_log.info("Withholding at {} resulted in average error of {} and std deviation of the"
					  " error of {} across {} runs".format(withholding, error_array.mean(), std, num_runs))

