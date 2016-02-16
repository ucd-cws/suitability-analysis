from django.shortcuts import render_to_response
from django.shortcuts import render

from relocation import models
# Create your views here.


def home(request):
	# do a bunch of stuff
	template_name = 'relocation/home.html'
	return render(request, template_name, {})


def parcel_viewer(request, parcels_id):
	template_name = 'relocation/parcels.html'
	parcels = models.PolygonStatistics.objects.get(pk=parcels_id)
	return render(request, template_name, context={'parcels': parcels})