from django.conf.urls import include, url
from . import views

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^parcels/(?P<parcels_id>\d+)/view$', views.parcel_viewer, name='parcels_view')
]