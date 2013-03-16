from django.conf.urls import patterns, url
from django.views.generic import DetailView, ListView
from forecast.models import Member, Party

urlpatterns = patterns('',
    url(r'^member/$',
        ListView.as_view(
          queryset=Member.objects.all(),
          context_object_name='members_list',
          template_name='forecast/member_choose.html'),
        name='members_choose'),
    url(r'^party/$',
        ListView.as_view(
          queryset=Party.objects.all(),
          context_object_name='parties_list',
          template_name='forecast/party_choose.html'),
        name='parties_choose'),
    url(r'^fetch/$', 'forecast.views.FetchAllData'),
    url(r'^predict/member/(?P<member_id>\d+)/$',
        'forecast.views.SelectFeaturesForMemberPrediction'),
    url(r'^predict/member/(?P<member_id>\d+)/bill/$',
        'forecast.views.BillOverviewForMemberPrediction'),
    url(r'^predict/party/(?P<party_id>\d+)/$',
        'forecast.views.SelectFeaturesForPartyPrediction'),
)
