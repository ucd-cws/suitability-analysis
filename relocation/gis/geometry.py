import logging
import traceback
import os

import arcpy

from relocation.gis.temp import generate_gdb_filename
from relocation.gis import temp

geoprocessing_log = logging.getLogger("geoprocessing")


def isiterable(item):
	"""tests whether an object is iterable

	TODO: May be replacable with just return hasattr() - not super useful, but prevents needing to remember the syntax and names
	"""
	if hasattr(item, '__iter__'):
		return True
	else:
		return False


def get_centroids(feature=None, method="FEATURE_TO_POINT", dissolve=False, as_file=False, id_field=False):
	"""
		Given an input polygon, this function returns a list of arcpy.Point objects that represent the centroids

	:param feature: str location of a shapefile or feature class
	:param method: str indicating the method to use to obtain the centroid. Possible values are "FEATURE_TO_POINT"
		(default - more accurate) and "ATTRIBUTE" (faster, but error-prone)
	:param dissolve: boolean flag indicating whether or not to dissolve the input features befor obtaining centroids
	:param as_file: boolean flag indicating whether to return the data as a file instead of a point list
	:param id_field: when included, means to pull ids into a tuple with the centroid from the specified field
	:return: list of arcpy.Point objects
	:raise:
	"""
	methods = ("FEATURE_TO_POINT", "ATTRIBUTE",)  # "MEAN_CENTER","MEDIAN_CENTER")

	if method not in methods:
		geoprocessing_log.warning("Centroid determination method is not in the set {0:s}".format(methods))
		return []

	if not feature:
		raise NameError("get_centroids requires a feature as input")

	if not check_type(feature, "Polygon"):
		geoprocessing_log.warning("Type of feature in get_centroids is not Polygon")
		return []

	if dissolve:  # should we pre-dissolve it?
		t_name = generate_gdb_filename("dissolved", gdb="in_memory")
		try:
			arcpy.Dissolve_management(feature, t_name, multi_part=True)
			feature = t_name
		except:
			geoprocessing_log.warning("Couldn't dissolve features first. Continuing anyway, but the results WILL be different than expected")

	if method == "ATTRIBUTE":
		points = centroid_attribute(feature, id_field=id_field)
		if as_file:
			if len(points) > 0:
				return_points = write_features_from_list(points, data_type="POINT", filename=None, spatial_reference=feature, write_ids=id_field)  # write_ids = id_field works because it just needs to set it to a non-false value
			else:
				return_points = None

	elif method == "FEATURE_TO_POINT":
		try:
			if as_file:
				return_points = centroid_feature_to_point(feature,as_file=True, id_field=id_field)
			else:
				points = centroid_feature_to_point(feature, id_field=id_field)
		except:
			err_str = traceback.format_exc()
			geoprocessing_log.warning("failed to obtain centroids using feature_to_point method. traceback follows:\n {0:s}".format(err_str))

	if as_file:
		return return_points
	else:
		return points


def check_type(feature=None,feature_type=None, return_type=False):
	"""

	:param feature:
	:param feature_type:
	:param return_type:
	:return:
	"""

	if not feature:
		geoprocessing_log.warning("no features in check_type")
		return False

	if not feature_type:
		geoprocessing_log.warning("no data_type(s) to check against in ")
		return False

	desc = arcpy.Describe(feature)

	if desc.dataType == "FeatureClass" or desc.dataType == "FeatureLayer":
		read_feature_type = desc.shapeType
	else:
		geoprocessing_log.error("feature parameter supplied to 'check_type' is not a FeatureClass")
		del desc
		return False

	del desc

	if return_type:
		return read_feature_type

	if isiterable(feature):  # if it's an iterable and we have multiple values for the feature_type, then check the whole list
		if read_feature_type in feature_type:
			return True
	elif read_feature_type == feature_type:  # if it's a single feature, just check them
		return True

	return False  # return False now


def write_features_from_list(data=None, data_type="POINT", filename=None, spatial_reference=None, write_ids=False):
	'''takes an iterable of feature OBJECTS and writes them out to a new feature class, returning the filename'''

	if not spatial_reference:
		geoprocessing_log.error("No spatial reference to write features out to in write_features_from_list")
		return False

	if not data:
		geoprocessing_log.error("Input data to write_features_from_list does not exist")
		return False

	if not isiterable(data):  # check if exists and that it's Iterable
		geoprocessing_log.error("Input data to write_features_from_list is not an Iterable. If you have a single item, pass it in as part of an iterable (tuple or list) please")

	filename = temp.check_spatial_filename(filename, create_filename=True, allow_fast=False)
	if not filename:
		geoprocessing_log.error("Error in filename passed to write_features_from_list")
		return False

	data_types = ("POINT", "MULTIPOINT", "POLYGON", "POLYLINE")
	if not data_type in data_types:
		geoprocessing_log.error("data_type passed into write_features from list is not in data_types")
		return False

	path_parts = os.path.split(filename)
	geoprocessing_log.info(str(path_parts))
	arcpy.CreateFeatureclass_management(path_parts[0],path_parts[1],data_type,'','','',spatial_reference)

	if write_ids is True:  # if we're supposed to write out the IDs, add a field
		id_field = "feature_id"
		arcpy.AddField_management(filename, id_field, "Long")
	else:
		id_field = False

	valid_datatypes = (arcpy.Point, arcpy.Polygon, arcpy.Polyline, arcpy.Multipoint)

	geoprocessing_log.info("writing shapes to %s" % filename)
	inserter = arcpy.InsertCursor(filename)
	primary_datatype = None

	geoprocessing_log.info("writing %s shapes" % len(data))
	#i=0
	for feature in data:
		cont_flag = True  # skip this by default if it's not a valid datatype

		if id_field:  # if we're supposed to wirte id_fields, then we have tuples instead, where the first item is the feature, and the second is the ID
			feature_id = feature[1]
			feature_shape = feature[0]
		else:
			feature_shape = feature


		if primary_datatype:
			if isinstance(feature_shape, primary_datatype):
				cont_flag = False
		else:
			for dt in valid_datatypes:
				if isinstance(feature_shape, dt):
					cont_flag = False  # check the object against all of the valid datatypes and make sure it's a class instance. If so, set this to false so we don't skip this feature
					primary_datatype = dt  # save what the datatype for this file is
		if cont_flag:
			geoprocessing_log.warning("Skipping a feature - mixed or unknown datatypes passed to write_features_from_list")
			continue
		try:
			in_feature = inserter.newRow()
			in_feature.shape = feature_shape

			if id_field:  # using this instead of if write_ids since they'll be effectively the same, and the IDE won't complain
				in_feature.setValue(id_field, feature_id)

			#i+=1
			#in_feature.rowid = i
			inserter.insertRow(in_feature)
		except:
			geoprocessing_log.error("Couldn't insert a feature into new dataset")
			continue

	del feature_shape
	del inserter

	return filename


def centroid_attribute(feature=None, id_field=False):
	'''for internal use only - gets the centroid using the polygon attribute method - if you want to determine centroids, use get_centroids()


	:param id_field: when included, means to pull ids into a tuple with the centroid from the specified field
	'''

	curs = arcpy.SearchCursor(feature)

	points = []
	for record in curs:
		points.append(record.shape.centroid)

	return points


def centroid_feature_to_point(feature,as_file=False, id_field=None):
	"""
	for internal use only

	:param feature: str feature class
	:param as_file: boolean indicates whether to return the arcpy file instead of returning the point array
	:param id_field: when included, means to pull ids into a tuple with the centroid from the specified field - can't return ids
	:return: list containing arcpy.Point objects
	"""
	if as_file:
		t_name = generate_gdb_filename("feature_to_point")  # we don't want a memory file if we are returning the filename
	else:
		t_name = generate_gdb_filename("feature_to_point", gdb="in_memory")

	arcpy.FeatureToPoint_management(feature, t_name, "CENTROID")

	if as_file:  # if asfile, return the filename, otherwise, make and return the point_array
		return t_name

	curs = arcpy.SearchCursor(t_name)  # open up the output

	points = []
	for record in curs:
		shape = record.shape.getPart()

		if id_field:
			shape_id = record.getValue(id_field)  # get the shape's point
			item = (shape, shape_id)
		else:
			item = shape

		points.append(item)

	arcpy.Delete_management(t_name)  # clean up the in_memory workspace
	del curs

	return points


def fast_dissolve(features, raise_error=True, base_name="dissolved"):
	out_name = generate_gdb_filename(base_name)
	try:
		arcpy.Dissolve_management(features, out_name)
	except:
		if raise_error is False:
			geoprocessing_log.warning("Couldn't dissolve. Returning non-dissolved layer")
			return features
		else:
			raise
	return out_name


def percent_overlap(feature_one, feature_two, dissolve=False):
	"""
	ArcGIS 10.1 and up. Not for 10.0
	:param feature_one:
	:param feature_two:
	:param dissolve:
	"""

	results = {
		'percent_overlap': None,
		'intersect_area': None,
		'union_area': None,
		'overlap_init_perspective': None,
		'overlap_final_perspective': None,
	}

	if dissolve:
		dissolved_init = fast_dissolve(feature_one)
		dissolved_final = fast_dissolve(feature_two)
	else:
		dissolved_init = feature_one
		dissolved_final = feature_two

	try:
		geoprocessing_log.info("Getting area of Initial...",)
		total_init_area = get_area(dissolved_init)

		geoprocessing_log.info("Getting area of Final...",)
		total_final_area = get_area(dissolved_final)
	except:
		geoprocessing_log.error("Couldn't get the areas")
		raise

	try:
		geoprocessing_log.info("Intersecting...",)
		intersect = temp.generate_fast_filename()
		arcpy.Intersect_analysis([dissolved_init, dissolved_final], intersect)

		int_curs = arcpy.da.SearchCursor(intersect, field_names=['SHAPE@AREA', ])
		int_areas = []
		for row in int_curs:
			int_areas.append(row[0])
		intersect_area = sum(int_areas)
		results['intersect_area'] = intersect_area
	except:
		geoprocessing_log.error("Couldn't Intersect")
		raise

	try:
		geoprocessing_log.info("Unioning...",)
		if len(int_areas) > 0:  # short circuit - if it's 0, we can return 0 as the value
			union = temp.generate_fast_filename()
			arcpy.Union_analysis([dissolved_init, dissolved_final], union)
		else:
			return results

		union_curs = arcpy.da.SearchCursor(union, field_names=['SHAPE@AREA'])
		union_areas = []
		for row in union_curs:
			union_areas.append(row[0])
		union_area = sum(union_areas)
		results['union_area'] = union_area
	except:
		geoprocessing_log.error("Couldn't Union")
		raise

	geoprocessing_log.info("Deleting temporary datasets and Calculating")

	arcpy.Delete_management(intersect)  # clean up - it's an in_memory dataset
	arcpy.Delete_management(union)  # clean up - it's an in_memory dataset

	results['percent_overlap'] = (float(intersect_area) / float(union_area)) * 100
	results['overlap_init_perspective'] = (float(intersect_area) / float(total_init_area)) * 100
	results['overlap_final_perspective'] = (float(intersect_area) / float(total_final_area)) * 100

	return results


def get_area(feature_class):
	'''returns the total area of a feature class'''

	temp_fc = generate_gdb_filename(return_full=True)
	arcpy.CalculateAreas_stats(feature_class, temp_fc)
	area_field = "F_AREA" # this is hardcoded, but now guaranteed because it is added to a copy and the field is updated if it already exists

	area_curs = arcpy.SearchCursor(temp_fc)
	total_area = 0
	for row in area_curs:
		total_area += row.getValue(area_field)
	del row
	del area_curs

	return total_area