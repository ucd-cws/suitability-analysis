from django.contrib import admin

from relocation import models

# Register your models here.

#from django.contrib.auth.admin import UserAdmin
#from django.contrib.auth.models import User
# Register your models here.

admin.site.register(models.Region)
admin.site.register(models.Location)
admin.site.register(models.LocationInformation)
admin.site.register(models.LocalSlopeConstraint)
admin.site.register(models.LandCoverConstraint)
admin.site.register(models.LandCoverChoice)
admin.site.register(models.ProtectedAreasConstraint)
admin.site.register(models.CensusPlacesConstraint)
admin.site.register(models.FloodplainAreasConstraint)
admin.site.register(models.SuitabilityAnalysis)
admin.site.register(models.Parcels)
