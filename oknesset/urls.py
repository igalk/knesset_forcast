from django.conf.urls import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'oknesset.views.main'),
    url(r'^forecast/', include('forecast.urls')),
    url(r'^db/', include('forecast.db')),
    url(r'^admin/', include(admin.site.urls)),
)
