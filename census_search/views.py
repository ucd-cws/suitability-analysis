from django.shortcuts import get_object_or_404, render
from .models import Place
import json
from django.http import HttpResponse

# Create your views here.
def place_list(request):
    return render(request, 'census_search/place_list.html', {})

def get_places(request):
    if request.is_ajax():
        q = request.GET.get('term', '')
        places = Place.objects.filter(city__icontains=q)
        results = []
        for pl in places:
            place_json = {}
            place_json = pl.city + "," + pl.state
            results.append(place_json)
        data = json.dumps(results)
    else:
        data = 'fail'
    mimetype = 'application/json'
    return HttpResponse(data, mimetype)

#gets and shows relevant geoJSON file for selection
def place_view(request, city, state):
    print(city)
    print(state)
    #file = get_object_or_404(Place, city=city, state=state).geojson
    return render(request, 'census_search/place_view.html', {})