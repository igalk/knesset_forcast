from django.conf.urls import patterns, url
from django.views.generic import DetailView, ListView
from forecast.models import Member

urlpatterns = patterns('',
    url(r'^erase/$', 'forecast.datautils.erase'),
)
