import cgi
import config
import os

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
from forecast.test_results import *
from search.words.bag_of_words import Build
from process import Process

def EscapeString(s):
  return cgi.escape(s).replace("\n", "<br/>").replace("\t", "&emsp;").replace(" ", "&nbsp;")

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
  if config.CACHE and os.path.exists(filename):
    progress.WriteProgress("Compile bag of words", 1, 1, True)
    progress.WriteProgress("Extract features", 1, 1, True)
    return
  
  feature_extractor = MemberBillsFeatureExtractor(progress)
  class_values = sorted(['FOR', 'AGAINST', 'ABSTAIN', 'NO_SHOW'])

  bills = [bill for bill in Bill.objects.all() if bill.vote_set.all()]

  # Build bag of words
  with Process('Building bag of words for member %s' % member.id):
    bag_of_words = Build(member=member, cutoff=0.65, progress=progress)

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

  open(filename, "w").write(content)

def FeatureDownloadForMember(request, member_id):
  arff_input = config.MemberPath(member_id)
  p = Progress()
  p.Reset()
  p.WriteProgress("Compile bag of words", 0, 1)
  p.WriteProgress("Extract features", 0, 1)
  p.WriteProgress("Run J48", 0, 1)
  MemberArffGenerate(member_id, arff_input, p)

  p.WriteProgress("Run J48", 1, 1)
  weka_runner = WekaRunner()
  weka_output = weka_runner.run(WekaRunner.CONFIGS["J48-0.25"], arff_input).raw_output
  p.WriteProgress("Run J48", 1, 1, True)

  weka_output = EscapeString(weka_output)
  return HttpResponse(weka_output)

def CompareAllMembers(request):
  p = Progress()
  p.Reset()

  members = Member.objects.all()
  p.WriteProgress("Compile bag of words", 0, 1)
  p.WriteProgress("Extract features", 0, 1)
  for conf_id in WekaRunner.CONFIGS:
    p.WriteProgress("Run %s" % conf_id, 0, 1)
  for i, member in enumerate(members):
    p.WriteProgress("Member %d/%d" % (i+1, len(members)), 0, 1)

  results = TestResults()
  weka_runner = WekaRunner()
  for i, member in enumerate(members):
    p.WriteProgress("Member %d/%d" % (i+1, len(members)), 1, 1)

    p.WriteProgress("Compile bag of words", 0, 1)
    p.WriteProgress("Extract features", 0, 1)
    for conf_id in WekaRunner.CONFIGS:
      p.WriteProgress("Run %s" % conf_id, 0, 1)

    arff_input = config.MemberPath(member.id)
    MemberArffGenerate(member.id, arff_input, p)

    for conf_id, conf in WekaRunner.CONFIGS.items():
      for j, split_percent in enumerate(WekaRunner.ALL_SPLITS):
        weka_output = weka_runner.run(conf, arff_input, split_percent)
        if weka_output.error:
          print "*"*40
          print "Weka Error"
          print weka_output.raw_output
          print "*"*40
        else:
          results.addResult(member.id, conf, split_percent, [1]*4, 1, weka_output)
        p.WriteProgress("Run %s" % conf_id, j+1, len(WekaRunner.ALL_SPLITS))
      p.WriteProgress("Run %s" % conf_id, 1, 1, True)

    p.WriteProgress("Member %d/%d" % (i+1, len(members)), 1, 1, True)

  results.exportCSV("/tmp/member.csv")
  return HttpResponse("DONE")

def ArffGenerateForMember(request, member_id):
  p = Progress()
  p.Reset()
  p.WriteProgress("Compile bag of words", 0, 1)
  p.WriteProgress("Extract features", 0, 1)
  MemberArffGenerate(member_id, config.MemberPath(member_id), p)
  return HttpResponse("File ready")

def ArffDownloadForMember(request, member_id):
  content = open(config.MemberPath(member_id), "r").read()
  response = HttpResponse(content, mimetype='application/octet-stream')
  response['Content-Disposition'] = "attachment; filename=member_votes_%s.arff" % member_id
  return response

def DownloadAllMembersComparison(request):
  content = open("/tmp/member.csv", "r").read()
  response = HttpResponse(content, mimetype='application/octet-stream')
  response['Content-Disposition'] = "attachment; filename=member_votes.csv"
  return response


def PartyArffGenerate(party_id, filename, progress):
  party = get_object_or_404(Party, pk=party_id)
  if config.CACHE and os.path.exists(filename):
    progress.WriteProgress("Compile bag of words", 1, 1, True)
    progress.WriteProgress("Extract features", 1, 1, True)
    return


  feature_extractor = PartyBillsFeatureExtractor(progress)
  class_values = sorted(['FOR', 'AGAINST', 'ABSTAIN', 'NO_SHOW'])

  bills = [bill for bill in Bill.objects.all() if bill.vote_set.all()]

  # Build bag of words
  with Process('Building bag of words for party %s' % party.id):
    bag_of_words = Build(party=party, cutoff=0.65, progress=progress)

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

  open(filename, "w").write(content)

def FeatureDownloadForParty(request, party_id):
  arff_input = config.PartyPath(party_id)
  p = Progress()
  p.Reset()
  p.WriteProgress("Compile bag of words", 0, 1)
  p.WriteProgress("Extract features", 0, 1)
  p.WriteProgress("Run J48", 0, 1)
  PartyArffGenerate(party_id, arff_input, p)

  p.WriteProgress("Run J48", 1, 1)
  weka_runner = WekaRunner()
  weka_output = weka_runner.run(WekaRunner.CONFIGS["J48-0.25"], arff_input).raw_output
  p.WriteProgress("Run J48", 1, 1, True)

  weka_output = EscapeString(weka_output)
  return HttpResponse(weka_output)

def CompareAllParties(request):
  p = Progress()
  p.Reset()

  parties = Party.objects.all()
  p.WriteProgress("Compile bag of words", 0, 1)
  p.WriteProgress("Extract features", 0, 1)
  for conf in WekaRunner.CONFIGS:
    p.WriteProgress("Run %s" % conf, 0, 1)
  for i, party in enumerate(parties):
    p.WriteProgress("Party %d/%d" % (i+1, len(parties)), 0, 1)

  for i, party in enumerate(parties):
    p.WriteProgress("Party %d/%d" % (i+1, len(parties)), 1, 1)

    p.WriteProgress("Compile bag of words", 0, 1)
    p.WriteProgress("Extract features", 0, 1)
    for conf in WekaRunner.CONFIGS:
      p.WriteProgress("Run %s" % conf, 0, 1)

    arff_input = config.PartyPath(party.id)
    PartyArffGenerate(party.id, arff_input, p)

    for conf in WekaRunner.CONFIGS:
      p.WriteProgress("Run %s" % conf, 1, 1)
      weka_runner = WekaRunner()
      weka_output = weka_runner.run(WekaRunner.CONFIGS[conf], arff_input).raw_output
      p.WriteProgress("Run %s" % conf, 1, 1, True)

    p.WriteProgress("Party %d/%d" % (i+1, len(parties)), 1, 1, True)

  return HttpResponse("DONE")

def ArffGenerateForParty(request, party_id):
  p = Progress()
  p.Reset()
  p.WriteProgress("Compile bag of words", 0, 1)
  p.WriteProgress("Extract features", 0, 1)
  PartyArffGenerate(party_id, config.PartyPath(party_id), p)
  return HttpResponse("File ready")

def ArffDownloadForParty(request, party_id):
  content = open(config.PartyPath(party_id), "r").read()
  response = HttpResponse(content, mimetype='application/octet-stream')
  response['Content-Disposition'] = "attachment; filename=party_votes_%s.arff" % party_id
  return response

def DownloadAllPartiesComparison(request):
  content = "fake"
  response = HttpResponse(content, mimetype='application/octet-stream')
  response['Content-Disposition'] = "attachment; filename=party_votes.csv"
  return response
