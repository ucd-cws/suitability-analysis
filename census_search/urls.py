from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^search/$', views.place_list, name='place_list'),
    url(r'^api/get_places/', views.get_places, name='get_places'),
    url(r'^search/view/(?P<state>.+?)/(?P<city>.+?)/$', views.place_view, name='place_view'),

]