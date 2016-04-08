# Code source: Gaël Varoquaux
# Modified for documentation by Jaques Grobler
# License: BSD 3 clause

import logging

from relocation.management import load

import numpy as np
import matplotlib.pyplot as plt

from sklearn import linear_model, decomposition, datasets
from sklearn.pipeline import Pipeline
from sklearn.grid_search import GridSearchCV
from sklearn.ensemble import RandomForestClassifier

processing_log = logging.getLogger("processing_log")

def scale_center(in_array):
	mean = in_array.mean(axis=0)  # make it give the mean calculated by each column
	std = in_array.std(axis=0)  # std deviation by column
	result = (in_array - mean)/std

	return result

def test_model(model_class=RandomForestClassifier, withhold=10000, chosen_index=-1):

	# TODO: chosen_index only works for -1 right now...

	model = model_class()

	raw_data = load.get_relocation_information_as_ndarray()

	# this goes before we separate data and targets
	np.random.shuffle(raw_data)  # shuffle the array so that we don't have one town at the bottom and we can get a mix

	# separate scale data and targets
	scale_data = raw_data[:, :chosen_index]
	targets = raw_data[:, chosen_index]
	data = scale_center(scale_data)  # remove the mean and divide by SD to give them all same scale

	X_data = data[:-withhold]  # load in the data, withholding the required number of records
	Y_data = targets[:-withhold]  # load in the targets, withholding the required number of records

	#try:
	return model.fit(X_data,Y_data), data[-withhold:], targets[-withhold:]
	#except:
	#	processing_log.error("Error fitting data - not raising error - returning X and Y data instead for inspection")
	#	return X_data, Y_data


def validate_model(model, withheld_data, withheld_targets):
	correct = 0
	incorrect = 0
	underpredict = 0
	overpredict = 0

	for index, record in enumerate(withheld_data):
		prediction = model.predict(record)
		result = prediction == withheld_targets[index]  # returns an object still

		if result == True:  # not an "is" - "is" fails here, but == works - TODO: Look into that
			correct += 1
		else:
			incorrect += 1

			if withheld_targets[index] == 1:
				underpredict += 1
			else:
				overpredict += 1

	processing_log.info("Percent Correct: {0:s}".format(str((correct/(correct+incorrect)))))

	return correct, incorrect, underpredict, overpredict


def run_and_validate(withhold=10000):

	model, x_validate, y_validate = test_model(withhold=withhold)

	correct, incorrect, underpredict, overpredict = validate_model(model, x_validate, y_validate)

	processing_log.info("Correctly predicted: {}".format(correct))
	processing_log.info("Incorrectly predicted: {}".format(incorrect))
	processing_log.info("Underpredicted: {}".format(underpredict))
	processing_log.info("Overpredicted: {}".format(overpredict))

	return model, x_validate, y_validate


def nick_test():
	logistic = linear_model.LogisticRegression()

	pca = decomposition.PCA()
	pipe = Pipeline(steps=[('pca', pca), ('logistic', logistic)])

	raw_data = load.get_relocation_information_as_ndarray()
	data = scale_center(raw_data)  # remove the mean and divide by SD to give them all same scale

	X_data = data[:,:-1]  # load in all the data for now, but strip off the targets
	Y_data = data[:,-1]   # load in all the targets
	###############################################################################
	# Plot the PCA spectrum
	pca.fit(X_data)

	plt.figure(1, figsize=(4, 3))
	plt.clf()
	plt.axes([.2, .2, .7, .7])
	plt.plot(pca.explained_variance_, linewidth=2)
	plt.axis('tight')
	plt.xlabel('n_components')
	plt.ylabel('explained_variance_')

	###############################################################################
	# Prediction

	n_components = 11
	Cs = np.logspace(-4, 4, 3)

	# Parameters of pipelines can be set using ‘__’ separated parameter names:

	estimator = GridSearchCV(pipe,
							 dict(logistic__C=Cs))
	estimator.fit(X_data, Y_data)

	#plt.axvline(estimator.best_estimator_.named_steps['pca'].n_components,
	#			linestyle=':', label='n_components chosen')
	plt.legend(prop=dict(size=12))
	plt.show()

def test():
	logistic = linear_model.LogisticRegression()

	pca = decomposition.PCA()
	pipe = Pipeline(steps=[('pca', pca), ('logistic', logistic)])

	digits = datasets.load_digits()
	X_digits = digits.data
	y_digits = digits.target

	###############################################################################
	# Plot the PCA spectrum
	pca.fit(X_digits)

	plt.figure(1, figsize=(4, 3))
	plt.clf()
	plt.axes([.2, .2, .7, .7])
	plt.plot(pca.explained_variance_, linewidth=2)
	plt.axis('tight')
	plt.xlabel('n_components')
	plt.ylabel('explained_variance_')

	###############################################################################
	# Prediction

	n_components = [20, 40, 64]
	Cs = np.logspace(-4, 4, 3)

	#Parameters of pipelines can be set using ‘__’ separated parameter names:

	estimator = GridSearchCV(pipe,
							 dict(pca__n_components=n_components,
								  logistic__C=Cs))
	estimator.fit(X_digits, y_digits)

	plt.axvline(estimator.best_estimator_.named_steps['pca'].n_components,
				linestyle=':', label='n_components chosen')
	plt.legend(prop=dict(size=12))
	plt.show()
