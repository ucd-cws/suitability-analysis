from django.conf.urls import include, url
from . import views

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^(?P<object_type>parcels)/(?P<item_id>\d+)/view$', views.polystats_viewer, name='parcels_view'),
    url(r'^(?P<object_type>location)/(?P<item_id>\d+)/view$', views.polystats_viewer, name='location_view')
]