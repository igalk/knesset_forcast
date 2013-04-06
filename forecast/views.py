import cgi

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from forecast.data_populator import DataPopulator
from forecast.feature import *
from forecast.models import *
from forecast.member_bills_feature_extractor import *
from forecast.party_bills_feature_extractor import *
from forecast.weka import WekaRunner
from forecast.progress import *
from search.words.bag_of_words import Build
from process import Process

def FetchAllData(request):
  DataPopulator().PopulateAllData()
  return HttpResponseRedirect(reverse('members_choose'))

def ReportProgress(request):
  p = Progress()
  progresses = ",".join([("{\"name\": \"%(name)s\", \"progress\": %(progress)d, \"done\": %(done)s}" % {
    "name":     v[0],
    "progress": int(v[1])*100 / int(v[2]),
    "done":     (len(v) > 3 and "true" or "false")
  }) for v in p.GetProgresses()])
  return HttpResponse("[" + progresses + "]")

def MemberArffGenerate(member_id, filename, progress):
  member = get_object_or_404(Member, pk=member_id)
  
  progress.Reset()
  feature_extractor = MemberBillsFeatureExtractor(progress)
  class_values = sorted(['FOR', 'AGAINST', 'ABSTAIN', 'NO_SHOW'])

  bills = [bill for bill in Bill.objects.all() if bill.vote_set.all()]

  # Build bag of words
  # with Process('Building bag of words for member %s' % member.id):
  #   bag_of_words = Build(member=member)

  # Build features
  with Process('Building features for member %s (%s bills)' % (member.id, len(bills))):
    features = MemberBillsFeatures()#bag_of_words)

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

  open(filename, "w").write(content)

def FeatureDownloadForMember(request, member_id):
  arff_input = "/tmp/member_votes_%s.arff" % member_id
  p = Progress()
  MemberArffGenerate(member_id, arff_input, p)

  p.WriteProgress("Running J48", 1, 1)
  weka_runner = WekaRunner()
  weka_output = weka_runner.run(WekaRunner.J48, arff_input)
  p.WriteProgress("Running J48", 1, 1, True)

  weka_output = cgi.escape(weka_output).replace("\n", "<br/>").replace("\t", "&emsp;")
  return HttpResponse(weka_output)

def ArffGenerateForMember(request, member_id):
  MemberArffGenerate(member_id, "/tmp/member_votes_%s.arff" % member_id, Progress())
  return HttpResponse("File ready")

def ArffDownloadForMember(request, member_id):
  content = open("/tmp/member_votes_%s.arff" % member_id, "r").read()
  response = HttpResponse(content, mimetype='application/octet-stream')
  response['Content-Disposition'] = "attachment; filename=member_votes_%s.arff" % member_id
  return response



def PartyArffGenerate(party_id, filename, progress):
  party = get_object_or_404(Party, pk=party_id)

  progress.Reset()
  feature_extractor = PartyBillsFeatureExtractor(progress)
  class_values = sorted(['FOR', 'AGAINST', 'ABSTAIN', 'NO_SHOW'])

  bills = [bill for bill in Bill.objects.all() if bill.vote_set.all()]

  # Build bag of words
  # with Process('Building bag of words for party %s' % party.id):
  #   bag_of_words = Build(party=party)

  # Build features
  with Process('Building features for party %s (%s bills)' % (party.id, len(bills))):
    features = PartyBillsFeatures() #bag_of_words)

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

  open(filename, "w").write(content)

def FeatureDownloadForParty(request, party_id):
  arff_input = "/tmp/party_votes_%s.arff" % party_id
  p = Progress()
  PartyArffGenerate(party_id, arff_input, p)

  p.WriteProgress("Running J48", 1, 1)
  weka_runner = WekaRunner()
  weka_output = weka_runner.run(WekaRunner.J48, arff_input)
  p.WriteProgress("Running J48", 1, 1, True)

  weka_output = cgi.escape(weka_output).replace("\n", "<br/>").replace("\t", "&emsp;")
  return HttpResponse(weka_output)

def ArffGenerateForParty(request, party_id):
  PartyArffGenerate(party_id, "/tmp/party_votes_%s.arff" % party_id, Progress())
  return HttpResponse("File ready")

def ArffDownloadForParty(request, party_id):
  content = open("/tmp/party_votes_%s.arff" % party_id, "r").read()
  response = HttpResponse(content, mimetype='application/octet-stream')
  response['Content-Disposition'] = "attachment; filename=party_votes_%s.arff" % party_id
  return response
