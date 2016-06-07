import logging
from random import shuffle

from FloodMitigation.settings import CHOSEN_FIELD

import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.ensemble import RandomForestClassifier

from relocation.models import RelocatedTown
from relocation.gis import conversion

processing_log = logging.getLogger("processing_log")

class ModelRunner(object):
	"""
		The ModelRunner class manages communicating with the database and running the model.
		It has methodds that load the data in an appropriate format from the database, then shuffle the records,
		rescale the values to be appropriate for a model, withhold records, fit a model, and retrieve feature importance.
		It acts as a sort of glue between the model objects from scikit-learn and our datastore.

		Sample workflow:

		from relocation.regression import random_forests
		model = random_forests.ModelRunner()  # create the object
		model.load_data()  # loads all of the relocation town data to the model - this step usually takes the longest (2-5 min on dev machine)
		model.run_and_validate()  # handles all of the necessary transformations. outputs basic validation information.
		model.feature_importance()  # pulls information from the model vectorizer and outputs a report of feature importance to the screen

		As of this writing, the ability to use this code to predict new locations is in progress
	"""

	classifier = RandomForestClassifier
	original_data = None
	chosen_field = CHOSEN_FIELD
	_data = None
	_targets = None
	_vectorizer = None
	_pulled_data = None  # saved for debugging
	fields = None
	model = None
	withheld_data = None
	withheld_truth = None
	number_records = None
	number_withheld = None

	correct = 0
	incorrect = 0
	underpredict = 0
	overpredict = 0

	percent_incorrect = 0

	def scale_center(self, data):
		mean = data.mean(axis=0)  # make it give the mean calculated by each column
		std = data.std(axis=0)  # std deviation by column
		return (data - mean) / std

	def load_data(self, load_towns=None, randomize=True, exclude_fields=()):

		data_records = []

		for town in RelocatedTown.objects.all():
			if load_towns and town.name not in load_towns:
				continue

			processing_log.info("Loading town {0:s}".format(town.name))
			new_data = conversion.features_to_dicts(town.parcels.layer, chosen_field=self.chosen_field)
			data_records += new_data

		if randomize:
			shuffle(data_records)  # randomize them before passing them . Works in place

		self._pulled_data = data_records
		self.vectorize_split_and_save(data_records)

	def reshuffle(self):
		shuffle(self._pulled_data)  # randomize them before passing them . Works in place
		self.vectorize_split_and_save(self._pulled_data)

	def vectorize_split_and_save(self, records):
		self._vectorizer = DictVectorizer()

		feature_data = self._vectorizer.fit_transform(records).toarray()  # don't need it, but need to call fit_transform to make get_feature_names work

		self.fields = self._vectorizer.get_feature_names()
		chosen_index = self.fields.index(self.chosen_field)
		feature_length = len(self.fields)

		# reattach them together
		spliced_feature_data = np.concatenate((feature_data[:,:chosen_index], feature_data[:,chosen_index+1:feature_length]), axis=1)
		chosen_data = feature_data[:, chosen_index]
		self.fields.remove(self.chosen_field)  # remove it from the fields now too

		self.original_data = spliced_feature_data
		self._targets = chosen_data
		self._data = self.scale_center(self.original_data)  # remove the mean and divide by SD to give them all same scale

	def withhold_and_fit_model(self, withhold=.1):

		model = self.classifier()

		self.number_records = self._data.shape[0]
		self.number_withheld = int(withhold * self.number_records)

		X_data = self._data[:-self.number_withheld]  # load in the data, withholding the required number of records
		Y_data = self._targets[:-self.number_withheld]  # load in the targets, withholding the required number of records

		# try:

		self.model = model.fit(X_data, Y_data)
		self.withheld_data = self._data[-self.number_withheld:]
		self.withheld_truth = self._targets[-self.number_withheld:]

	def validate(self):

		if not self.model:
			raise ValueError("Must have fit model before validating")

		self.correct = 0
		self.incorrect = 0
		self.underpredict = 0
		self.overpredict = 0

		for index, record in enumerate(self.withheld_data):
			prediction = self.model.predict(record.reshape([1, -1]))  # need to reshape in order to avoid a DeprecationWarning (and deprecated feature)
			result = prediction == self.withheld_truth[index]  # returns an object still

			if result == True:  # not an "is" - "is" fails here, but == works - TODO: Look into that
				self.correct += 1
			else:
				self.incorrect += 1

				if self.withheld_truth[index] == 1:
					self.underpredict += 1
				else:
					self.overpredict += 1

		processing_log.info("Percent Correct: {0:s}".format(str((self.correct / (self.correct + self.incorrect)))))

	def run_and_validate(self, withhold=.1):

		self.withhold_and_fit_model(withhold=withhold)

		total_y_trues = np.count_nonzero(self.withheld_truth)
		self.validate()

		processing_log.info("Total records: {}".format(self.number_records))
		processing_log.info("Number of withheld records: {}".format(self.number_withheld))

		processing_log.info("Correctly predicted: {}".format(self.correct))
		processing_log.info("Incorrectly predicted: {}".format(self.incorrect))
		processing_log.info("Underpredicted: {}".format(self.underpredict))
		processing_log.info("Overpredicted: {}".format(self.overpredict))

		self.percent_incorrect = self.underpredict / total_y_trues

		processing_log.info("Total 'True' values in validation dataset: {}".format(total_y_trues))
		processing_log.info("Percent incorrect for True: {}".format(self.percent_incorrect))

	def feature_importance(self):

		features_and_values = {}

		for index, value in enumerate(self.model.feature_importances_):
			features_and_values[value] = self.fields[index]  # indexing by value so that we can sort

		sorted_keys = list(features_and_values.keys())
		sorted_keys.sort()

		for value in sorted_keys:
			processing_log.info("{}: {}".format(features_and_values[value], value))

	def predict_new_dataset(self):
		"""
		It's going to need to load up the new parcels, and make sure that it adds a blank chosen
		field to each record (so that it can be put through the same vectorizer - it may not need this, so confirm)

		then read in the records one by one, putting each one through the vectorizer, then predicting, and then setting
		the value on the parcels at the same time.
		:return:
		"""

		pass