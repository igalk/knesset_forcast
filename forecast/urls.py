from django.conf.urls import patterns, url
from django.views.generic import DetailView, ListView
from forecast.models import Member

urlpatterns = patterns('',
    url(r'^$',
        ListView.as_view(
          queryset=Member.objects.all(),
          context_object_name='members_list',
          template_name='forecast/member_choose.html'),
        name='members_choose'),
    url(r'^fetch/$', 'forecast.views.FetchMembers'),
    url(r'^predict/member/(?P<member_id>\d+)/$',
        'forecast.views.SelectFeaturesForMemberPrediction'),
    url(r'^predict/member/(?P<member_id>\d+)/bill/$',
        'forecast.views.BillOverviewForMemberPrediction'),
)
