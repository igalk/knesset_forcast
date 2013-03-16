from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from forecast.data_populator import DataPopulator
from forecast.models import Bill, Member
from forecast.member_bills_feature_extractor import MemberBillsFeatures
from forecast.member_bills_feature_extractor import MemberBillsFeatureExtractor
from search.words.bag_of_words import Build

def FetchAllData(request):
  DataPopulator().PopulateAllData()
  return HttpResponseRedirect(reverse('members_choose'))

def SelectFeaturesForMemberPrediction(request, member_id):
  member = get_object_or_404(Member, pk=member_id)
  bag_of_words = Build(member_id)
  return render_to_response('forecast/predict_member.html', {
      'member': member,
      'features': MemberBillsFeatures(bag_of_words),
    }, context_instance=RequestContext(request))

def BillOverviewForMemberPrediction(request, member_id):
  member = get_object_or_404(Member, pk=member_id)
  bills = Bill.objects.all()

  bag_of_words = Build(member_id)
  features = MemberBillsFeatures(bag_of_words)

  params = request.POST.keys()
  params.sort()
  selected_features = []
  for param in params:
    if param.startswith('feature'):
      selected_features.append(features[int(param[len('feature'):])-1])

  feature_extractor = MemberBillsFeatureExtractor()
  feature_values = feature_extractor.Extract(member, bills, selected_features)
  return render_to_response('forecast/overview_bill.html', {
      'features': selected_features,
      'feature_values': [{
          'bill': bill,
          'feature_values': feature_values[bill.id][0],
        } for bill in bills],
    })
