from django.shortcuts import render_to_response
from django.shortcuts import render

from relocation import models
# Create your views here.


def home(request):
	# do a bunch of stuff
	template_name = 'relocation/home.html'
	return render(request, template_name, {})



def polystats_viewer(request, object_type, item_id):
	template_name = 'relocation/polystats.html'

	if object_type == "parcels":
		object = models.Parcels.objects.get(pk=item_id)
	elif object_type == "location":
		object = models.location.objects.get(pk=item_id)

	return render(request, template_name, context={'object': object, 'object_type': object_type.title()})

def parcel_viewer(request, parcels_id):
	template_name = 'relocation/parcels.html'
	parcels = models.Parcels.objects.get(pk=parcels_id)
	return render(request, template_name, context={'parcels': parcels})

