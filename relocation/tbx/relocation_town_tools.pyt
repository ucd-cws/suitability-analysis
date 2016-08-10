import arcpy

import os
import sys


##### SET UP DJANGO TO BE USED OUTSIDE OF DJANGO
# hardcode it for now. Don't want to go dealing with installation and the registry
base_folder = r"C:\Users\dsx.AD3\Code\FloodMitigation"

if "DJANGO_SETTINGS_MODULE" not in os.environ:
	sys.path.insert(0, base_folder)
	os.environ['DJANGO_SETTINGS_MODULE'] = "FloodMitigation.settings"

os.chdir(base_folder)

import django
django.setup()

from relocation.models import RelocatedTown

##### DJANGO SETUP COMPLETE


def get_nested_object_from_string(initial_object, object_string):
	"""
		Given a string that describes a subobject, this deconstructs it based on the periods and returns the
		actual object that is described.
	:param initial_object:
	:param object_string:
	:return:
	"""
	parts = object_string.split(".")
	current_obj = initial_object
	for part in parts:
		current_obj = getattr(current_obj, part)

	return current_obj


def make_output_param(params, name, displayName, symbology=None):
	param = arcpy.Parameter(
		name=name,
		displayName=displayName,
		datatype="DEFeatureClass",
		parameterType="Derived",
		direction="Output"
	)
	if symbology:
		param.symbology = os.path.join(base_folder, "relocation", "tbx", symbology)

	params.append(param)

def make_index(params):
	item_index = {}
	for index, value in enumerate(params):
		item_index[value.name] = index

	return item_index

def make_load_town_params():

	items = [
		# short_name/key, name, attribute on the moved town, layer to symbolize with
		("before_structures", "Before Structures", "before_structures", "old_structures.lyr"),
		("moved_structures", "Moved Structures", "moved_structures", "new_structures.lyr"),
		("unfiltered_before_structures", "Unfiltered Before Structures", "unfiltered_before_structures", "old_structures.lyr"),
		("unfiltered_moved_structures", "Unfiltered Moved Structures", "unfiltered_moved_structures", "all_structures_incl_nonpermanent.lyr"),
		("before_location", "Before Boundary", "before_location.boundary_polygon", "old_boundary.lyr"),
		("moved_location", "Moved Boundary", "moved_location.boundary_polygon", "new_boundary.lyr"),
		("dem", "DEM", "region.dem", None),
		("slope", "Slope", "region.slope", None),
		("land_cover", "Land Cover", "region.land_cover", None),
		("protected_areas", "Protected Areas", "region.protected_areas", "PAD.lyr"),
		("floodplain_areas", "Floodplain Areas", "region.floodplain_areas", "nfhl.lyr"),
		("roads", "Roads", "region.roads", "roads.lyr"),
		("rivers", "Rivers", "region.rivers", "NHD.lyr"),
		("barrier_river", "Barrier River", "region.barrier_river", "major_river.lyr"),
		("parcels", "Parcels", "parcels.layer", "parcels.lyr"),
	]

	towns = [town.name for town in RelocatedTown.objects.all()]

	town_param = arcpy.Parameter(
		name="town",
		displayName="Town to load",
		datatype="GPString",
		parameterType="Required",
		direction="Input"
	)

	town_param.filter.type = "ValueList"
	town_param.filter.list = towns

	items_param = arcpy.Parameter(
		name="items",
		displayName="Items to Load",
		datatype="GPString",
		parameterType="Required",
		direction="Input",
		multiValue=True
	)

	items_param.filter.type = "ValueList"
	items_param.filter.list = [item[1] for item in items]

	params = [town_param, items_param]
	for item in items:
		make_output_param(params, item[0], item[1], item[3])

	return params, make_index(params), items


class Toolbox(object):
	def __init__(self):
		"""Define the toolbox (the name of the toolbox is the name of the
		.pyt file)."""
		self.label = "RelocationTownTools"
		self.alias = "Relocation Town Tools"

		# List of tool classes associated with this toolbox
		self.tools = [Load_Town]


class Load_Town(object):
	def __init__(self):
		"""Define the tool (tool name is the name of the class)."""
		self.label = "Load Town to Current Map"
		self.description = ""
		self.canRunInBackground = False

	def getParameterInfo(self):
		"""Define parameter definitions"""

		params, item_index, items = make_load_town_params()
		return params

	def isLicensed(self):
		"""Set whether tool is licensed to execute."""
		return True

	def updateParameters(self, parameters):
		"""Modify the values and properties of parameters before internal
		validation is performed.  This method is called whenever a parameter
		has been changed."""
		return

	def updateMessages(self, parameters):
		"""Modify the messages created by internal validation for each tool
		parameter.  This method is called after internal validation."""
		return

	def execute(self, parameters, messages):
		"""The source code of the tool."""

		params, item_index, items = make_load_town_params()

		town_name = parameters[0].valueAsText
		items_to_load = parameters[1].valueAsText
		town = RelocatedTown.objects.get(name=town_name)
		arcpy.AddMessage("Items to Load: {}".format(items_to_load))
		items_to_load = items_to_load.split(";")

		for item in items:
			if item[1] not in items_to_load and "'{}'".format(item[1]) not in items_to_load:
				arcpy.AddMessage("Skipping item {}".format(item[1]))
				continue

			try:
				arcpy.SetParameterAsText(item_index[item[0]], get_nested_object_from_string(town,item[2]))
			except AttributeError:
				arcpy.AddWarning("Failed to load {}".format(item[0]))

