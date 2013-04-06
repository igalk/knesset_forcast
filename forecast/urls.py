from django.conf.urls import patterns, url
from django.views.generic import DetailView, ListView
from forecast.models import Member, Party

urlpatterns = patterns('',
    url(r'^fetch/$', 'forecast.views.FetchAllData'),
    url(r'^progress$', 'forecast.views.ReportProgress'),
    url(r'^member/$',
        ListView.as_view(
          queryset=Member.objects.all(),
          context_object_name='members_list',
          template_name='forecast/member_choose.html'),
        name='members_choose'),
    url(r'^member/(?P<member_id>\d+)/$',
        'forecast.views.FeatureDownloadForMember'),
    url(r'^member/(?P<member_id>\d+)/arff$',
        'forecast.views.ArffGenerateForMember'),
    url(r'^member/(?P<member_id>\d+)/arff/download$',
        'forecast.views.ArffDownloadForMember'),
    url(r'^party/$',
        ListView.as_view(
          queryset=Party.objects.all(),
          context_object_name='parties_list',
          template_name='forecast/party_choose.html'),
        name='parties_choose'),
    url(r'^party/(?P<party_id>\d+)/$',
        'forecast.views.FeatureDownloadForParty'),
    url(r'^party/(?P<party_id>\d+)/arff$',
        'forecast.views.ArffGenerateForParty'),
    url(r'^party/(?P<party_id>\d+)/arff/download$',
        'forecast.views.ArffDownloadForParty'),
)
