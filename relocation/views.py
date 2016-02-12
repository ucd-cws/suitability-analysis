from django.shortcuts import render_to_response
from django.shortcuts import render

# Create your views here.


def home(request):
	# do a bunch of stuff
	template_name = 'relocation/home.html'
	return render(request, template_name, {})