from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from forecast.data_populator import DataPopulator
from forecast.feature import *
from forecast.models import *
from forecast.member_bills_feature_extractor import *
from forecast.party_bills_feature_extractor import *
from search.words.bag_of_words import Build
from process import Process

def FetchAllData(request):
  DataPopulator().PopulateAllData()
  return HttpResponseRedirect(reverse('members_choose'))

def SelectFeaturesForMemberPrediction(request, member_id):
  member = get_object_or_404(Member, pk=member_id)
  bag_of_words = Build(member=member)
  return render_to_response('forecast/predict_member.html', {
      'member': member,
      'features': MemberBillsFeatures(bag_of_words),
    }, context_instance=RequestContext(request))

def BillOverviewForMemberPrediction(request, member_id):
  member = get_object_or_404(Member, pk=member_id)
  bills = [bill for bill in Bill.objects.all() if bill.vote_set.all()]

  bag_of_words = Build(member=member)
  features = MemberBillsFeatures(bag_of_words)

  params = request.POST.keys()
  params.sort()
  selected_features = []
  for param in params:
    if param.startswith('feature'):
      selected_features.append(features[int(param[len('feature'):])-1])

  feature_extractor = MemberBillsFeatureExtractor()
  feature_names = []
  for feature in selected_features:
    if isinstance(feature, FeatureSet):
      feature_names.extend([f.name for f in feature.features])
    else:
      feature_names.append(feature.name)
  feature_values = feature_extractor.Extract(member, bills, selected_features)
  return render_to_response('forecast/overview_bill.html', {
      'feature_names': feature_names,
      'feature_values': [{
          'bill': bill,
          'feature_values': feature_values[bill.id][0],
        } for bill in bills],
    })

def FeatureDownloadForMember(request, member_id):
  member = get_object_or_404(Member, pk=member_id)

  feature_extractor = MemberBillsFeatureExtractor()
  class_values = sorted(['FOR', 'AGAINST', 'ABSTAIN', 'NO_SHOW'])

  # votes = Vote.objects.filter(votememberdecision__member_id=member.id)
  # bills = Bill.objects.filter(vote__id__in=[vote.id for vote in votes])
  bills = [bill for bill in Bill.objects.all() if bill.vote_set.all()]

  # Build bag of words
  with Process('Building bag of words for member %s' % member.id):
    bag_of_words = Build(member=member)

  # Build features
  with Process('Building features for member %s (%s bills)' % (member.id, len(bills))):
    features = MemberBillsFeatures(bag_of_words)

    extracted = feature_extractor.Extract(member, bills, features)
    feature_values = [sorted(feature.LegalValues()) for feature in features]

  # Output features to arff
  content = ''
  with Process('Outputing arff for member %s' % member.id):
    content += '@RELATION decision\n\n'
    for feature in features:
      if isinstance(feature, FeatureSet):
        classes = feature.class_name()
        values = feature.LegalValues()
        for i, class_name in enumerate(classes):
          content += '@ATTRIBUTE %s {%s}\n' % (class_name,
                                               ','.join([str(v) for v in values[i]]))
      else:
        content += '@ATTRIBUTE %s {%s}\n' % (feature.class_name(),
                                             ','.join([str(v) for v in feature.LegalValues()]))
    content += '@ATTRIBUTE class {%s}\n\n' % ','.join(class_values)

    content += '@DATA\n'
    values = extracted.values()
    values.sort(key=lambda v: v[2])
    for value in values:
      content += ','.join([','.join([str(v) for v in value[0]]), value[1]]) + '\n'

  response = HttpResponse(content, mimetype='application/octet-stream')
  response['Content-Disposition'] = "attachment; filename=member_votes_%s.arff" % member.id
  return response

def SelectFeaturesForPartyPrediction(request, party_id):
  party = get_object_or_404(Party, pk=party_id)
  bag_of_words = Build(party=party)
  return render_to_response('forecast/predict_party.html', {
      'party': party,
      'features': PartyBillsFeatures(bag_of_words),
    }, context_instance=RequestContext(request))

def BillOverviewForPartyPrediction(request, party_id):
  party = get_object_or_404(Party, pk=party_id)
  bills = [bill for bill in Bill.objects.all() if bill.vote_set.all()]

  bag_of_words = Build(party=party)
  features = PartyBillsFeatures(bag_of_words)

  params = request.POST.keys()
  params.sort()
  selected_features = []
  for param in params:
    if param.startswith('feature'):
      selected_features.append(features[int(param[len('feature'):])-1])

  feature_extractor = PartyBillsFeatureExtractor()
  feature_names = []
  for feature in selected_features:
    if isinstance(feature, FeatureSet):
      feature_names.extend([f.name for f in feature.features])
    else:
      feature_names.append(feature.name)
  feature_values = feature_extractor.Extract(party, bills, selected_features)
  return render_to_response('forecast/overview_bill.html', {
      'feature_names': feature_names,
      'feature_values': [{
          'bill': bill,
          'feature_values': feature_values[bill.id][0],
        } for bill in bills],
    })

def FeatureDownloadForParty(request, party_id):
  party = get_object_or_404(Party, pk=party_id)

  feature_extractor = PartyBillsFeatureExtractor()
  class_values = sorted(['FOR', 'AGAINST', 'ABSTAIN', 'NO_SHOW'])

  # votes = set()
  # for member in party.member_set.all():
  #   votes = votes.union(Vote.objects.filter(votememberdecision__member_id=member.id))
  # bills = Bill.objects.filter(vote__id__in=[vote.id for vote in votes])
  bills = [bill for bill in Bill.objects.all() if bill.vote_set.all()]

  # Build bag of words
  with Process('Building bag of words for party %s' % party.id):
    bag_of_words = Build(party=party)

  # Build features
  with Process('Building features for party %s (%s bills)' % (party.id, len(bills))):
    features = PartyBillsFeatures(bag_of_words)

    extracted = feature_extractor.Extract(party, bills, features)
    feature_values = [sorted(feature.LegalValues()) for feature in features]

  # Output features to arff
  content = ''
  with Process('Outputing arff for party %s' % party.id):
    content += '@RELATION decision\n\n'
    for feature in features:
      if isinstance(feature, FeatureSet):
        classes = feature.class_name()
        values = feature.LegalValues()
        for i, class_name in enumerate(classes):
          content += '@ATTRIBUTE %s {%s}\n' % (class_name,
                                               ','.join([str(v) for v in values[i]]))
      else:
        content += '@ATTRIBUTE %s {%s}\n' % (feature.class_name(),
                                             ','.join([str(v) for v in feature.LegalValues()]))
    content += '@ATTRIBUTE class {%s}\n\n' % ','.join(class_values)

    content += '@DATA\n'
    values = extracted.values()
    values.sort(key=lambda v: v[2])
    for value in values:
      content += ','.join([','.join([str(v) for v in value[0]]), value[1]]) + '\n'

  response = HttpResponse(content, mimetype='application/octet-stream')
  response['Content-Disposition'] = "attachment; filename=party_votes_%s.arff" % party.id
  return response
