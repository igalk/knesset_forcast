import cgi
import config
import itertools
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
from forecast.generic_bills_feature_extractor import *
from forecast.weka import WekaRunner
from forecast.progress import *
from forecast.test_results import *
from search.words.bag_of_words import Build
from process import Process
from django.views.decorators.csrf import csrf_exempt

import logging
logger = logging.getLogger('django')   # Django's catch-all logger
hdlr = logging.StreamHandler()   # Logs to stderr by default
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.WARNING)

MEMBER_FEATURE_TO_IGNORE = [
    (5, 9),     # Coalition features.
    (10, 43),   # Agenda features.
    (44, 537),  # Tag features.
    538,        # BoW feature.
  ]
PARTY_FEATURE_TO_IGNORE = [
    (3, 7),     # Coalition features.
    (8, 41),    # Agenda features.
    (42, 535),  # Tag features.
    536,        # BoW feature.
  ]

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

def ConfigsList(request):
  algorithms = "{\"id\": \"algorithm\", \"category\": \"Algorithm\", \"type\": \"multi\", \"options\": [" + ",".join([("{\"name\": \"%(name)s\"}" % {
    "name": config
  }) for config in WekaRunner.CONFIGS]) + "]}"

  splits = "{\"id\": \"split\", \"category\": \"Split\", \"type\": \"multi\", \"options\": [" + ",".join([("{\"name\": \"%(name)s\"}" % {
    "name": split
  }) for split in WekaRunner.ALL_SPLITS]) + "]}"

  use_coalition = "{\"id\": \"use_coalition\", \"category\": \"Use coalition structure\", \"type\": \"bool\"}"
  use_agendas = "{\"id\": \"use_agendas\", \"category\": \"Use agendas\", \"type\": \"bool\"}"
  use_tags = "{\"id\": \"use_tags\", \"category\": \"Use tags\", \"type\": \"bool\"}"
  use_bag_of_words = "{\"id\": \"use_bag_of_words\", \"category\": \"Use bag of words\", \"type\": \"bool\"}"
  use_wildcards = "{\"id\": \"use_wildcards\", \"category\": \"Use wild cards\", \"type\": \"bool\"}"

  configs = "[%s, %s, %s, %s, %s, %s, %s]" % (algorithms, splits, use_coalition, use_agendas, use_tags, use_bag_of_words, use_wildcards)
  return HttpResponse(configs)

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

  no_wildcards_content = content.replace("?", "0")
  open(filename.replace(".arff", ".nowc.arff"), "w").write(no_wildcards_content)

@csrf_exempt
def FeatureDownloadForMember(request, member_id):
  algorithm = request.POST["optionsalgorithm"]
  split = request.POST["optionssplit"]
  features_to_use = tuple((
    request.POST["optionsuse_coalition"] == 'true',
    request.POST["optionsuse_agendas"] == 'true',
    request.POST["optionsuse_tags"] == 'true',
    request.POST["optionsuse_bag_of_words"] == 'true',
  ))
  features_to_ignore = [feature_range for f, feature_range in enumerate(MEMBER_FEATURE_TO_IGNORE)
                                      if not features_to_use[f]]
  use_wildcards = (request.POST["optionsuse_wildcards"] == 'true')

  arff_input = config.MemberPath(member_id)
  if not use_wildcards:
    arff_input = arff_input.replace(".arff", ".nowc.arff")

  p = Progress()
  p.Reset()
  p.WriteProgress("Compile bag of words", 0, 1)
  p.WriteProgress("Extract features", 0, 1)
  p.WriteProgress("Run %s" % algorithm, 0, 1)
  MemberArffGenerate(member_id, arff_input, p)

  p.WriteProgress("Run %s" % algorithm, 1, 1)
  weka_runner = WekaRunner()
  weka_output = weka_runner.run(WekaRunner.CONFIGS[algorithm], arff_input, split, features_to_ignore).raw_output
  p.WriteProgress("Run %s" % algorithm, 1, 1, True)

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

  results = TestResults("/tmp/member.csv")
  weka_runner = WekaRunner()
  for i, member in enumerate(members):
    p.WriteProgress("Member %d/%d" % (i+1, len(members)), 1, 1)

    p.WriteProgress("Compile bag of words", 0, 1)
    p.WriteProgress("Extract features", 0, 1)
    for conf_id in WekaRunner.CONFIGS:
      p.WriteProgress("Run %s" % conf_id, 0, 1)

    arff_input = config.MemberPath(member.id)
    arff_inputs = [arff_input.replace(".arff", ".nowc.arff"), arff_input]
    MemberArffGenerate(member.id, arff_input, p)

    total_iterations = len(WekaRunner.ALL_SPLITS) * (2**len(MEMBER_FEATURE_TO_IGNORE)) * len(arff_inputs)
    for conf_id, conf in WekaRunner.CONFIGS.items():
      print "Checking conf_id = %s" % conf_id
      j = 0
      for split_percent in WekaRunner.ALL_SPLITS:
        print "Checking split = %s" % split_percent
        features_to_use_iters = tuple([[0, 1] for r in MEMBER_FEATURE_TO_IGNORE])
        print "Checking features_to_use_iters = %s" % (features_to_use_iters,)
        for features_to_use in itertools.product(*features_to_use_iters):
          print "Checking features_to_use = %s" % (features_to_use,)
          feature_sets_to_ignore = [feature_range for f, feature_range in enumerate(MEMBER_FEATURE_TO_IGNORE)
                                    if not features_to_use[f]]
          print "Checking feature_sets_to_ignore = %s" % feature_sets_to_ignore
          for use_wildcards, arff_input in enumerate(arff_inputs):
            print "Checking use_wildcards = %s" % use_wildcards
            weka_output = weka_runner.run(conf, arff_input, split_percent, feature_sets_to_ignore)
            if weka_output.error:
              print "*"*40
              print "Weka Error"
              print weka_output.raw_output
              print "*"*40
            else:
              results.addResult(member.id, conf, split_percent, features_to_use, use_wildcards, weka_output)
            j += 1
            p.WriteProgress("Run %s" % conf_id, j, total_iterations)
      p.WriteProgress("Run %s" % conf_id, 1, 1, True)

    p.WriteProgress("Member %d/%d" % (i+1, len(members)), 1, 1, True)

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

  no_wildcards_content = content.replace("?", "0")
  open(filename.replace(".arff", ".nowc.arff"), "w").write(no_wildcards_content)

@csrf_exempt
def FeatureDownloadForParty(request, party_id):
  algorithm = request.POST["optionsalgorithm"]
  split = request.POST["optionssplit"]
  features_to_use = tuple((
    request.POST["optionsuse_coalition"] == 'true',
    request.POST["optionsuse_agendas"] == 'true',
    request.POST["optionsuse_tags"] == 'true',
    request.POST["optionsuse_bag_of_words"] == 'true',
  ))
  features_to_ignore = [feature_range for f, feature_range in enumerate(PARTY_FEATURE_TO_IGNORE)
                                      if not features_to_use[f]]
  use_wildcards = (request.POST["optionsuse_wildcards"] == 'true')

  arff_input = config.PartyPath(party_id)
  if not use_wildcards:
    arff_input = arff_input.replace(".arff", ".nowc.arff")
  p = Progress()
  p.Reset()
  p.WriteProgress("Compile bag of words", 0, 1)
  p.WriteProgress("Extract features", 0, 1)
  p.WriteProgress("Run %s" % algorithm, 0, 1)
  PartyArffGenerate(party_id, arff_input, p)

  p.WriteProgress("Run %s" % algorithm, 1, 1)
  weka_runner = WekaRunner()
  weka_output = weka_runner.run(WekaRunner.CONFIGS[algorithm], arff_input, split, features_to_ignore).raw_output
  p.WriteProgress("Run %s" % algorithm, 1, 1, True)

  weka_output = EscapeString(weka_output)
  return HttpResponse(weka_output)

def CompareAllParties(request):
  p = Progress()
  p.Reset()

  parties = Party.objects.all()
  p.WriteProgress("Compile bag of words", 0, 1)
  p.WriteProgress("Extract features", 0, 1)
  for conf_id in WekaRunner.CONFIGS:
    p.WriteProgress("Run %s" % conf_id, 0, 1)
  for i, party in enumerate(parties):
    p.WriteProgress("Party %d/%d" % (i+1, len(parties)), 0, 1)

  results = TestResults("/tmp/party.csv")
  weka_runner = WekaRunner()
  for i, party in enumerate(parties):
    p.WriteProgress("Party %d/%d" % (i+1, len(parties)), 1, 1)

    p.WriteProgress("Compile bag of words", 0, 1)
    p.WriteProgress("Extract features", 0, 1)
    for conf_id in WekaRunner.CONFIGS:
      p.WriteProgress("Run %s" % conf_id, 0, 1)

    arff_input = config.PartyPath(party.id)
    arff_inputs = [arff_input.replace(".arff", ".nowc.arff"), arff_input]
    PartyArffGenerate(party.id, arff_input, p)

    total_iterations = len(WekaRunner.ALL_SPLITS) * (2**len(PARTY_FEATURE_TO_IGNORE)) * len(arff_inputs)
    for conf_id, conf in WekaRunner.CONFIGS.items():
      print "Checking conf_id = %s" % conf_id
      j = 0
      for split_percent in WekaRunner.ALL_SPLITS:
        print "Checking split = %s" % split_percent
        features_to_use_iters = tuple([[0, 1] for r in PARTY_FEATURE_TO_IGNORE])
        print "Checking features_to_use_iters = %s" % (features_to_use_iters,)
        for features_to_use in itertools.product(*features_to_use_iters):
          print "Checking features_to_use = %s" % (features_to_use,)
          feature_sets_to_ignore = [feature_range for f, feature_range in enumerate(PARTY_FEATURE_TO_IGNORE)
                                    if not features_to_use[f]]
          print "Checking feature_sets_to_ignore = %s" % feature_sets_to_ignore
          for use_wildcards, arff_input in enumerate(arff_inputs):
            print "Checking use_wildcards = %s" % use_wildcards
            weka_output = weka_runner.run(conf, arff_input, split_percent, feature_sets_to_ignore)
            if weka_output.error:
              print "*"*40
              print "Weka Error"
              print weka_output.raw_output
              print "*"*40
            else:
              results.addResult(party.id, conf, split_percent, features_to_use, use_wildcards, weka_output)
            j += 1
            p.WriteProgress("Run %s" % conf_id, j, total_iterations)
      p.WriteProgress("Run %s" % conf_id, 1, 1, True)

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
  content = open("/tmp/party.csv", "r").read()
  response = HttpResponse(content, mimetype='application/octet-stream')
  response['Content-Disposition'] = "attachment; filename=party_votes.csv"
  return response

def ArffGenerateGeneric(request):
  p = Progress()
  p.Reset()
  p.WriteProgress("Extract features", 0, 1)

  feature_extractor = GenericBillsFeatureExtractor(p)
  class_values = sorted(['FOR', 'AGAINST', 'ABSTAIN'])

  bills = [bill for bill in Bill.objects.all() if bill.vote_set.all()]

  # Build features
  with Process('Building generic features'):
    features = GenericBillsFeatures()

    extracted = feature_extractor.Extract(bills, features)
    feature_values = [sorted(feature.LegalValues()) for feature in features]

  # Output features to arff
  content = ''
  with Process('Outputing generic arff'):
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

  open('features/generic.arff', "w").write(content)

  no_wildcards_content = content.replace("?", "0")
  open('features/generic.nowc.arff', "w").write(no_wildcards_content)
  
  response = HttpResponse(content, mimetype='application/octet-stream')
  response['Content-Disposition'] = "attachment; filename=all_votes.arff"
  return response
