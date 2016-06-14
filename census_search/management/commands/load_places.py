from django.core.management.base import BaseCommand, CommandError
from census_search.models import Place
import arcpy

class Command(BaseCommand):
    help = 'Loads data to database'

    def handle(self, *args, **options):
        self.stdout.write("Loading data...")

        rows = arcpy.SearchCursor("C:\\Users\\Lawrence\\Documents\\ArcGIS\\Projects\\census_search\\census_search.gdb\\city_states",
                      fields="OBJECTID; cb_2014_Merge_NAME; FPName_STATENAME")

        # Iterate through the rows in the cursor
        for row in rows:
            '''print("key: {0}, City: {1}, State: {2}".format(
                row.getValue("OBJECTID"),
                row.getValue("cb_2014_Merge_NAME"),
                row.getValue("FPName_STATENAME")))'''
            p1 = Place()
            p1.key = row.getValue("OBJECTID")
            p1.city = row.getValue("cb_2014_Merge_NAME")
            p1.state = row.getValue("FPName_STATENAME")

            filename = "city_" + p1.key
            layer = "C:\\Users\\Lawrence\\PycharmProjects\\suitability-analysis\\census_search\\static\\geojson\\layers\\SBA city_states\\SBA.gdb\\" + filename

            p1.layer = layer
            p1.as_geojson() #create the gsojson file and set the attribute for its location
            p1.save()

        self.stdout.write("Done.")