# Author: ESRI
# Date:   August 2010
#
# Purpose: This script creates a concave hull polygon FC using a k-nearest neighbours approach
#          modified from that of A. Moreira and M. Y. Santos, Univeristy of Minho, Portugal.
#          It identifies a polygon which is the region occupied by an arbitrary set of points
#          by considering at least "k" nearest neighbouring points (30 >= k >= 3) amongst the set.
#          If input points have uneven spatial density then any value of k may not connect the
#          point "clusters" and outliers will be excluded from the polygon.  Pre-processing into
#          selection sets identifying clusters will allow finding hulls one at a time.  If the
#          found polygon does not enclose the input point features, higher values of k are tried
#          up to a maximum of 30.
#
# Author: Richard Fairhurst
# Date:   February 2012
#
# Update:  The script was enhanced by Richard Fairhurst to include an optional case field parameter.
#          The case field can be any numeric, string, or date field in the point input and is
#          used to sort the points and generate separate polygons for each case value in the output.
#          If the Case field is left blank the script will work on all input points as it did
#          in the original script.
#
#          A field named "POINT_CNT" is added to the output feature(s) to indicate the number of
#          unique point locations used to create the output polygon(s).
#
#          A field named "ENCLOSED" is added to the output feature(s) to indicates if all of the
#          input points were enclosed by the output polygon(s). An ENCLOSED value of 1 means all
#          points were enclosed. When the ENCLOSED value is 0 and Area and Perimeter are greater
#          than 0, either all points are touching the hull boundary or one or more outlier points
#          have been excluded from the output hull. Use selection sets or preprocess input data
#          to find enclosing hulls. When a feature with an ENCLOSED value of 0 and Empty or Null
#          geometry is created (Area and Perimeter are either 0 or Null) insufficient input points
#          were provided to create an actual polygon.
#
# Author: Richard Fairhurst
# Date:
#
# Update:  Revised script to use da module cursors and a case field dictionary to improve speed.

# Author: Nick Santos
# Date: 3/1/2016
#
# Update: Revised to make main body a function of its own for inclusion in suitability analysis code

import arcpy
import itertools
import math
import os
import sys
import traceback
import string

#arcpy.overwriteOutput = True

# Functions that consolidate reuable actions
#

# Function to return an OID list for k nearest eligible neighbours of a feature
def kNeighbours(k, oid, pDict, excludeList=[]):
	hypotList = [math.hypot(pDict[oid][0] - pDict[id][0], pDict[oid][1] - pDict[id][1]) for id in pDict.keys() if
				 id != oid and id not in excludeList]
	hypotList.sort()
	hypotList = hypotList[0:k]
	oidList = [id for id in pDict.keys() if math.hypot(pDict[oid][0] - pDict[id][0], pDict[oid][1] - pDict[id][
		1]) in hypotList and id != oid and id not in excludeList]
	return oidList


# Function to rotate a point about another point, returning a list [X,Y]
def RotateXY(x, y, xc=0, yc=0, angle=0):
	x = x - xc
	y = y - yc
	xr = (x * math.cos(angle)) - (y * math.sin(angle)) + xc
	yr = (x * math.sin(angle)) + (y * math.cos(angle)) + yc
	return [xr, yr]


# Function finding the feature OID at the rightmost angle from an origin OID, with respect to an input angle
def Rightmost(oid, angle, pDict, oidList):
	origxyList = [pDict[id] for id in pDict.keys() if id in oidList]
	rotxyList = []
	for p in range(len(origxyList)):
		rotxyList.append(RotateXY(origxyList[p][0], origxyList[p][1], pDict[oid][0], pDict[oid][1], angle))
	minATAN = min([math.atan2((xy[1] - pDict[oid][1]), (xy[0] - pDict[oid][0])) for xy in rotxyList])
	rightmostIndex = rotxyList.index(
		[xy for xy in rotxyList if math.atan2((xy[1] - pDict[oid][1]), (xy[0] - pDict[oid][0])) == minATAN][0])
	return oidList[rightmostIndex]


# Function to detect single-part polyline self-intersection
def selfIntersects(polyline):
	lList = []
	selfIntersects = False
	for n in range(0, len(polyline.getPart(0)) - 1):
		lList.append(arcpy.Polyline(arcpy.Array([polyline.getPart(0)[n], polyline.getPart(0)[n + 1]])))
	for pair in itertools.product(lList, repeat=2):
		if pair[0].crosses(pair[1]):
			selfIntersects = True
			break
	return selfIntersects


# Function to construct the Hull
def createHull(pDict, outCaseField, lastValue, kStart, dictCount, includeNull, sR, outFC):
	# Value of k must result in enclosing all data points; create condition flag
	enclosesPoints = False
	notNullGeometry = False
	k = kStart

	if dictCount > 1:
		pList = [arcpy.Point(xy[0], xy[1]) for xy in pDict.values()]
		mPoint = arcpy.Multipoint(arcpy.Array(pList), sR)
		minY = min([xy[1] for xy in pDict.values()])

		while not enclosesPoints and k <= 30:
			arcpy.AddMessage("Finding hull for k = " + str(k))
			# Find start point (lowest Y value)
			startOID = [id for id in pDict.keys() if pDict[id][1] == minY][0]
			# Select the next point (rightmost turn from horizontal, from start point)
			kOIDList = kNeighbours(k, startOID, pDict, [])
			minATAN = min(
				[math.atan2(pDict[id][1] - pDict[startOID][1], pDict[id][0] - pDict[startOID][0]) for id in kOIDList])
			nextOID = [id for id in kOIDList if
					   math.atan2(pDict[id][1] - pDict[startOID][1], pDict[id][0] - pDict[startOID][0]) == minATAN][0]
			# Initialise the boundary array
			bArray = arcpy.Array(arcpy.Point(pDict[startOID][0], pDict[startOID][1]))
			bArray.add(arcpy.Point(pDict[nextOID][0], pDict[nextOID][1]))
			# Initialise current segment lists
			currentOID = nextOID
			prevOID = startOID
			# Initialise list to be excluded from candidate consideration (start point handled additionally later)
			excludeList = [startOID, nextOID]
			# Build the boundary array - taking the closest rightmost point that does not cause a self-intersection.
			steps = 2
			while currentOID != startOID and len(pDict) != len(excludeList):
				try:
					angle = math.atan2((pDict[currentOID][1] - pDict[prevOID][1]),
									   (pDict[currentOID][0] - pDict[prevOID][0]))
					oidList = kNeighbours(k, currentOID, pDict, excludeList)
					nextOID = Rightmost(currentOID, 0 - angle, pDict, oidList)
					pcArray = arcpy.Array([arcpy.Point(pDict[currentOID][0], pDict[currentOID][1]), \
										   arcpy.Point(pDict[nextOID][0], pDict[nextOID][1])])
					while arcpy.Polyline(bArray, sR).crosses(arcpy.Polyline(pcArray, sR)) and len(oidList) > 0:
						# arcpy.AddMessage("Rightmost point from " + str(currentOID) + " : " + str(nextOID) + " causes self intersection - selecting again")
						excludeList.append(nextOID)
						oidList.remove(nextOID)
						oidList = kNeighbours(k, currentOID, pDict, excludeList)
						if len(oidList) > 0:
							nextOID = Rightmost(currentOID, 0 - angle, pDict, oidList)
							# arcpy.AddMessage("nextOID candidate: " + str(nextOID))
							pcArray = arcpy.Array([arcpy.Point(pDict[currentOID][0], pDict[currentOID][1]), \
												   arcpy.Point(pDict[nextOID][0], pDict[nextOID][1])])
					bArray.add(arcpy.Point(pDict[nextOID][0], pDict[nextOID][1]))
					prevOID = currentOID
					currentOID = nextOID
					excludeList.append(currentOID)
					# arcpy.AddMessage("CurrentOID = " + str(currentOID))
					steps += 1
					if steps == 4:
						excludeList.remove(startOID)
				except ValueError:
					arcpy.AddMessage(
						"Zero reachable nearest neighbours at " + str(pDict[currentOID]) + " , expanding search")
					break
			# Close the boundary and test for enclosure
			bArray.add(arcpy.Point(pDict[startOID][0], pDict[startOID][1]))
			pPoly = arcpy.Polygon(bArray, sR)
			if pPoly.length == 0:
				break
			else:
				notNullGeometry = True
			if mPoint.within(arcpy.Polygon(bArray, sR)):
				enclosesPoints = True
			else:
				arcpy.AddMessage("Hull does not enclose data, incrementing k")
				k += 1
		#
		if not mPoint.within(arcpy.Polygon(bArray, sR)):
			arcpy.AddWarning("Hull does not enclose data - probable cause is outlier points")

	# Insert the Polygons
	if (notNullGeometry and includeNull == False) or includeNull:
		if outCaseField is not None:
			insFields = [outCaseField, "POINT_CNT", "ENCLOSED", "SHAPE@"]
		else:
			insFields = ["POINT_CNT", "ENCLOSED", "SHAPE@"]
		rows = arcpy.da.InsertCursor(outFC, insFields)
		row = []
		if outCaseField is not None:
			row.append(lastValue)
		row.append(dictCount)
		if notNullGeometry:
			row.append(enclosesPoints)
			row.append(arcpy.Polygon(bArray, sR))
		else:
			row.append(-1)
			row.append(None)
		rows.insertRow(row)
		del row
		del rows
	elif outCaseField is not None:
		arcpy.AddMessage("\nExcluded Null Geometry for case value " + str(lastValue) + "!")
	else:
		arcpy.AddMessage("\nExcluded Null Geometry!")


def concave_hull(in_points, k, out_fc, case_field=None):
	# Get the input feature class or layer
	in_desc = arcpy.Describe(in_points)
	in_path = os.path.dirname(in_desc.CatalogPath)
	spatial_reference = in_desc.spatialReference

	# Get k
	k_start = k

	# Get output Feature Class
	out_path = os.path.dirname(out_fc)
	out_name = os.path.basename(out_fc)

	# Get case field and ensure it is valid
	if case_field is not None:
		fields = in_desc.fields
		for field in fields:
			# Check the case field type
			if field.name == case_field:
				case_field_type = field.type
				if case_field_type not in ["SmallInteger", "Integer", "Single", "Double", "String", "Date"]:
					arcpy.AddMessage(
						"\nThe Case Field named " + case_field + " is not a valid case field type!  The Case Field will be ignored!\n")
					case_field = " "
				else:
					if case_field_type in ["SmallInteger", "Integer", "Single", "Double"]:
						case_field_length = 0
						case_field_scale = field.scale
						case_field_precision = field.precision
					elif case_field_type == "String":
						case_field_length = field.length
						case_field_scale = 0
						case_field_precision = 0
					else:
						case_field_length = 0
						case_field_scale = 0
						case_field_precision = 0

	# Define an output case field name that is compliant with the output feature class
	out_case_field = str.upper(str(case_field))
	if out_case_field == "ENCLOSED":
		out_case_field = "ENCLOSED1"
	if out_case_field == "POINT_CNT":
		out_case_field = "POINT_CNT1"
	if out_fc.split(".")[-1] in ("shp", "dbf"):
		out_case_field = out_case_field[0, 10]  # field names in the output are limited to 10 charaters!

	# Get Include Null Geometry Feature flag
	if arcpy.GetParameterAsText(4) == "true":
		include_null = True
	else:
		include_null = False

	# Some housekeeping
	in_desc = arcpy.Describe(in_points)
	arcpy.env.OutputCoordinateSystem = spatial_reference
	oidName = str(in_desc.OIDFieldName)
	if in_desc.dataType == "FeatureClass":
		in_points = arcpy.MakeFeatureLayer_management(in_points)

	# Create the output
	arcpy.AddMessage("\nCreating Feature Class...")
	out_fc = arcpy.CreateFeatureclass_management(out_path, out_name, "POLYGON", "#", "#", "#", spatial_reference).getOutput(0)
	if case_field is not None:
		if case_field_type in ["SmallInteger", "Integer", "Single", "Double"]:
			arcpy.AddField_management(out_fc, out_case_field, case_field_type, str(case_field_scale), str(case_field_precision))
		elif case_field_type == "String":
			arcpy.AddField_management(out_fc, out_case_field, case_field_type, "", "", str(case_field_length))
		else:
			arcpy.AddField_management(out_fc, out_case_field, case_field_type)
	arcpy.AddField_management(out_fc, "POINT_CNT", "Long")
	arcpy.AddField_management(out_fc, "ENCLOSED", "SmallInteger")

	# Build required data structures
	arcpy.AddMessage("\nCreating data structures...")
	rowCount = 0
	caseCount = 0
	dictCount = 0
	pDict = {}  # dictionary keyed on oid with [X,Y] list values, no duplicate points
	if case_field is not None:
		fields = [case_field, 'OID@', 'SHAPE@X', 'SHAPE@Y']
		valueDict = {}
		with arcpy.da.SearchCursor(in_points, fields) as searchRows:
			for searchRow in searchRows:
				keyValue = searchRow[0]
				if not keyValue in valueDict:
					# assign a new keyValue entry to the dictionary storing a list of the first NumberField value and 1 for the first record counter value
					valueDict[keyValue] = [[searchRow[1], searchRow[2], searchRow[3]]]
				# Sum the last summary of NumberField value with the current record and increment the record count when keyvalue is already in the dictionary
				else:
					valueDict[keyValue].append([searchRow[1], searchRow[2], searchRow[3]])
		for lastValue in sorted(valueDict):
			caseCount += 1
			for p in valueDict[lastValue]:
				rowCount += 1
				# Continue processing the current point subset.
				if [p[1], p[2]] not in pDict.values():
					pDict[p[0]] = [p[1], p[2]]
					dictCount += 1
			createHull(pDict, out_case_field, lastValue, k_start, dictCount, include_null, spatial_reference, out_fc)
			# Reset variables for processing the next point subset.
			pDict = {}
			dictCount = 0
	else:
		fields = ['OID@', 'SHAPE@X', 'SHAPE@Y']
		for p in arcpy.da.SearchCursor(in_points, fields):
			rowCount += 1
			if [p[1], p[2]] not in pDict.values():
				pDict[p[0]] = [p[1], p[2]]
				dictCount += 1
				lastValue = 0
		else:
			lastValue = 0
		# Final create hull call and wrap up of the program's massaging
		createHull(pDict, out_case_field, lastValue, k_start, dictCount, include_null, spatial_reference, out_fc)
	arcpy.AddMessage("\n" + str(rowCount) + " points processed.  " + str(caseCount) + " case value(s) processed.")
	if case_field == " " and arcpy.GetParameterAsText(3) is not None:
		arcpy.AddMessage(
			"\nThe Case Field named " + arcpy.GetParameterAsText(3) + " was not a valid field type and was ignored!")
	arcpy.AddMessage("\nFinished")
