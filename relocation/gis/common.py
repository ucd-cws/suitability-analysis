import os
import sys
import tempfile
import logging
import re

import arcpy

processing_log = logging.getLogger("processing_log")

delims_open = {'mdb': "[", "sqlite": "\"", 'gdb': "\"", 'shp': "\"", 'in_memory': ""}  # a dictionary of field delimiters for use in sql statements.
delims_close = {'mdb': "]", "sqlite": "\"", 'gdb': "\"", 'shp': "\"", 'in_memory': ""}  # in one type of field or another. These two are just extension based lookups


def mark_polygons(polygons_to_mark, marking_polygons, field_name, selection_type="INTERSECT"):
	"""
		Takes the parcels layer for the analysis object and adds a field that it uses to mark the parcels as chosen or not chosen
	"""

	# add field - default of 0

	arcpy.AddField_management(polygons_to_mark, field_name, "SHORT")
	arcpy.CalculateField_management(polygons_to_mark, field_name, "0", expression_type="PYTHON_9.3")

	# select by location the new boundary
	marking_layer = "marking_layer"
	arcpy.MakeFeatureLayer_management(polygons_to_mark, marking_layer)

	# select the parcels that are part of the new location, and mark the "chosen" field as a true value
	try:
		arcpy.SelectLayerByLocation_management(marking_layer, selection_type, marking_polygons)

		# calculate field doesn't seem to only operate on the selection when using Python - annoying. Using Cursor instead
		parcels = arcpy.UpdateCursor(marking_layer, fields=field_name)
		for record in parcels:
			record.setValue(field_name, "1")
			parcels.updateRow(record)
	finally:
		arcpy.Delete_management(marking_layer)


def copy_field(layer, field_from, field_to):
	fields = arcpy.ListFields(layer)

	source_field = None
	for field in fields:
		if field.name == field_from:
			source_field = field
	else:
		raise ValueError("field_from {} is not available on layer {}".format(field_from, layer))


class geospatial_object:

	def setup_object(self):
		'''like __init__ but won't be overridden by subclasses'''

		if 'setup_run' in self.__dict__:  # check if we have this key in a safe way
			if self.setup_run is True:  # have we already run this function
				return  # don't run it again

		self.setup_run = True
		self.gdb = None
		self.temp_folder = None
		self.temp_gdb = None

	def check_temp(self):
		self.setup_object()

		if not self.temp_folder or not self.temp_gdb:
			try:
				self.temp_folder = tempfile.mkdtemp()
				temp_gdb = os.path.join(self.temp_folder,"join_temp.gdb")
				if arcpy.Exists(temp_gdb):
					self.temp_gdb = temp_gdb
				else: # doesn't exist
					if 'log' in sys.modules:
						processing_log.info("Creating %s" % temp_gdb)
					arcpy.CreateFileGDB_management(self.temp_folder,"join_temp.gdb")
					self.temp_gdb = temp_gdb
			except:
				return False
		return True

	def get_temp_folder(self):
		self.setup_object()

		if self.check_temp():
			return self.temp_folder
		else:
			raise IOError("Couldn't create temp folder")

	def get_temp_gdb(self):
		self.setup_object()

		if self.check_temp():
			return self.temp_gdb
		else:
			raise IOError("Couldn't create temp gdb or folder")

	def split_items(self, features, gdb = None, feature_type = "POLYGON"):
		'''this could probably be done with an arcgis function - realized after writing...'''

		self.setup_object()

		if self.gdb is None:
			self.gdb = self.get_temp_gdb()

		if features is None: # use the instance's main file if the arg is none - it's not the default because eclipse was complaining about using "self" as an arg - may be possible, but haven't tested.
			features = self.main_file

		processing_log.info("Splitting features")

		features_name = os.path.splitext(os.path.split(features)[1])[0]

		desc = arcpy.Describe(features)

		has_id_col = None
		if desc.hasOID:
			has_id_col = True
			id_col = desc.OIDFieldName
		else:
			id_col = 0

		all_features = arcpy.SearchCursor(features)

		arcpy.MakeFeatureLayer_management(features,"t_features") # make it a feature layer so we can use it as a template

		tid = 0

		split_features = []

		for feature in all_features:
			if has_id_col:
				tid = feature.getValue(id_col)
			else:
				tid += 1

			feature_filename = "%s_%s_" % (features_name,tid)

			t_name = arcpy.CreateUniqueName(feature_filename,self.gdb)
			t_name_parts = os.path.split(t_name) # split it back out to feed into the next function
			processing_log.info("splitting out to %s" % t_name)

			# make a new feature class
			arcpy.CreateFeatureclass_management(t_name_parts[0],t_name_parts[1],feature_type,"t_features","DISABLED","DISABLED",desc.spatialReference)
			ins_curs = arcpy.InsertCursor(t_name)

			# copy this feature into it
			t_row = ins_curs.newRow()
			for field in desc.fields: # copy each field
				try:
					if field.editable:
						t_row.setValue(field.name,feature.getValue(field.name))
				except:
					processing_log.info("skipping col %s - can't copy" % field.name,False,"debug")
					continue

			t_row.shape = feature.shape # copy the shape over explicitly

			ins_curs.insertRow(t_row)

			split_features.append(t_name)

			try:
				del ins_curs # close the cursor
			except:
				continue

		del desc # kill the describe object
		arcpy.Delete_management("t_features") # delete the feature layer

		return split_features


class data_file(geospatial_object):
	def __init__(self,filename = None):
		self.data_location = filename
		self.delim_open = None
		self.delim_close = None

	def set_delimiters(self):

		processing_log.info("Setting delimiters",)

		try:
			fc_info = arcpy.ParseTableName(self.data_location)
			database, owner, featureclass = fc_info.split(",")
		except:
			processing_log.error("Failed to assess data format")
			return False

		processing_log.info("Type from ParseTableName = %s" % featureclass)

		if re.match(" mdb",featureclass) is not None or re.search("\.mdb",featureclass) is not None:
			self.delim_open = delims_open['mdb']
			self.delim_close = delims_close['mdb']
		elif re.match(" gdb",featureclass) is not None or re.search("\.gdb",featureclass) is not None:
			self.delim_open = delims_open['gdb']
			self.delim_close = delims_close['gdb']
		elif re.match(" shp",featureclass) is not None or re.search("\.shp",featureclass) is not None:
			self.delim_open = delims_open['shp']
			self.delim_close = delims_close['shp']
		elif re.match(" sqlite", featureclass) is not None or re.search("\.db", featureclass) is not None or re.search("\.sqlite", featureclass) is not None:
			self.delim_open = delims_open['sqlite']
			self.delim_close = delims_close['sqlite']
		elif re.match(" in_memory",featureclass) is not None or re.search("in_memory",featureclass) is not None: # dbmses use no delimeters. This is just a guess at how to detect if an fc is in one since I don't have access yet.
			self.delim_open = delims_open['in_memory']
			self.delim_close = delims_close['in_memory']
		elif re.match(" sde",featureclass) is not None:  # dbmses use no delimeters. This is just a guess at how to detect if an fc is in one since I don't have access yet.
			self.delim_open = ""
			self.delim_close = ""
		else:
			processing_log.warning("No field delimiters for this type of data. We can select features in gdbs, mdbs, shps, in_memory, and possibly sde files (untested)")
			return False

		return True
