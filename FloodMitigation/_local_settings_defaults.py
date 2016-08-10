import os
import logging

from FloodMitigation import gis

processing_log = logging.getLogger("processing_log")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCRATCH_GDB = os.path.join(BASE_DIR, "scratch", "scratch.gdb")

#try:
#	gis.clean_location(SCRATCH_GDB, path_type="FGDB")
#except:  # I know... but really, almost any error in this code is worth rolling through and seeing if we can proceed.
#	processing_log.warning("Unable to delete and recreate scratch workspace - if you run into random errors, try recreating the scratch geodatabase manually")

RUN_GEOPROCESSING = True # a flag that attempts to speed things up during debug in order to test code changes
EXCLUDE_OLD_BOUNDARY_FROM_NEW = True

MODEL_LAND_USE = False
MIN_MAX_MEAN_JOIN = ("MAX","MIN")  # determines which zonal stats to run
PARCEL_HEXAGON_SIDE_LENGTH = 142
# 142 was the default before being replaced with config variable.
# That default value came from monroe parcels - average parcel area is 53k m2. side length of hexagon with that area is 142
# However, that seems like maybe it doesn't capture enough variability in town. Trying other values

ZONAL_STATS_BUG = True  # a flag to tell some zonal stats based tools to use a workaround that fixes a bug.
# The bug occurs when using a polygon zone item - the data in the zonal table comes out incorrect (shifted by a column).
