import json
import re
import time
import traceback
import urllib
from BeautifulSoup import BeautifulSoup
import numpy
from forecast.models import *

from forecast.models import *

def OknessetURL(entity):
  return 'http://oknesset.org/api/v2/%s?format=json' % entity

def OknessetHTMLURL(entity):
  return 'http://oknesset.org/%s' % entity

def MemberURL(member_id=''):
  return OknessetURL('member/%s' % member_id)

def MemberHTMLURL(member_id=''):
  return OknessetHTMLURL('member/%s' % member_id)

def PartyURL(party_id=''):
  return OknessetURL('party/%s' % party_id)

class StatsFetcher:
  """
  This is the main class that populates the data into the DB.

  It scrapes the OpenKnesset website to get the data on all members.
  """
  def __init__(self):
    self.parties = {}
    self.members = {}

  def GetStats(self):
    self.GetPartyStats()
    self.GetMemberStats()
    self.GetBillVoteStats()

  def GetPartyStats(self):
    print '='*80
    print 'Fetching parties...'
    data = self._GetJSONData(PartyURL())

    if data['meta']['next']:
      raise Exception('Next is not expected in parties: %s' % data['meta']['next'])

    total = data['meta']['total_count']
    for i, data_item in enumerate(data['objects']):
      print 'Progress: (%d/%d)' % (i+1, total)
      party = self._PopulateParty(data_item)
      print '='*40

  def GetMemberStats(self):
    print '='*80
    print 'Fetching members...'
    data = self._GetJSONData(MemberURL())

    if data['meta']['next']:
      raise Exception('Next is not expected in members: %s' % data['meta']['next'])

    total = data['meta']['total_count']
    for i, data_item in enumerate(data['objects']):
      print 'Progress: (%d/%d)' % (i+1, total)
      member = self._PopulateMemberById(data_item['id'])
      print '='*40

    print 'Stats:'
    print 'Party discipline:'
    self.printStats([m['party_discipline'] for i, m in self.members.items() if 'party_discipline' in m], 'party_discipline')
    print '  100%%-ers:', sum([1 for i, m in self.members.items() if 'party_discipline' in m and m['party_discipline'] == 100.0])

    print 'Coalition discipline:'
    self.printStats([m['coalition_discipline'] for i, m in self.members.items() if 'coalition_discipline' in m], 'coalition_discipline')
    print '  100%%-ers:', sum([1 for i, m in self.members.items() if 'coalition_discipline' in m and m['coalition_discipline'] == 100.0])

    print 'Opposition discipline:'
    self.printStats([m['opposition_discipline'] for i, m in self.members.items() if 'opposition_discipline' in m], 'opposition_discipline')
    print '  100%%-ers:', sum([1 for i, m in self.members.items() if 'opposition_discipline' in m and m['opposition_discipline'] == 100.0])
    
    print 'Vote against own:'
    self.printStats([m['against_own'] for i, m in self.members.items()], 'against_own')

  def GetBillVoteStats(self):
    print 'Total number of bills:', len(Bill.objects.all())
    print 'Bills with votes:', len([b for b in Bill.objects.all() if len(b.vote_set.all()) > 0])
    print 'Total number of votes:', len(Vote.objects.all())
    print 'Number of approval votes:', len([v for v in Vote.objects.all() if v.type == 'approval'])

    vote_decisions = [v.votememberdecision_set.all() for v in Vote.objects.all()]
    print 'Averge voters per vote:', numpy.average([len(vd) for vd in vote_decisions])
    print 'Averge voters per vote with oppinion:', numpy.average([len([d for d in vd if d.decision in ['FOR', 'AGAINST']]) for vd in vote_decisions])
    print 'Average parties per vote:', numpy.average([len(set([d.member.party for d in vd])) for vd in vote_decisions])

  def _GetJSONData(self, url, max_tries=10, wait_between_retries=5):
    tries = 0
    exc = None
    while tries <= max_tries:
      try:
        cm = urllib.urlopen(url)
        data = json.load(cm)
        return data
      except IOError, e:
        exc = e
      except ValueError, e:
        exc = e

      time.sleep(wait_between_retries)
      tries += 1
      print "Retrying... (%d/%d)" % (tries, max_tries)
    else:
      print "--> URL = '%s'" % url
      if exc:
        print "IO ERROR:"
        print exc

    raise IOError("Too many IOErrors, aborting")

  def _GetHTMLData(self, url, max_tries=10, wait_between_retries=5):
    tries = 0
    exc = None
    while tries <= max_tries:
      try:
        cm = urllib.urlopen(url)
        data = cm.read()
        return BeautifulSoup(data)
      except IOError, e:
        exc = e
      except ValueError, e:
        exc = e

      time.sleep(wait_between_retries)
      tries += 1
      print "Retrying... (%d/%d)" % (tries, max_tries)
    else:
      print "--> URL = '%s'" % url
      if exc:
        print "IO ERROR:"
        print exc

    raise IOError("Too many IOErrors, aborting")

  def _PopulateParty(self, data_item):
    party_id = int(data_item['id'])
    print 'Looking at party %d' % party_id
    self.parties[party_id] = data_item

    return data_item

  def _PopulateMemberById(self, member_id):
    member_id = int(member_id)
    print 'Looking at member', member_id
    data = self._GetJSONData(MemberURL(member_id))
    if not data['is_current']:
      print 'Not current member, skipping'
      return
    soup = self._GetHTMLData(MemberHTMLURL(member_id))

    data['party_id'] = int(data['party_url'].split('/')[2])

    self.members[member_id] = {}
    self.members[member_id]['data'] = data
    
    try:
      self.members[member_id]['party_discipline'] = float(soup.findAll('label')[2].parent.span.text.replace('%',''))
      print 'party discipline:', self.members[member_id]['party_discipline']
    except:
      pass
    
    if self.parties[data['party_id']]['is_coalition']:
      try:
        self.members[member_id]['coalition_discipline'] = float(soup.findAll('label')[4].parent.span.text.replace('%',''))
        print 'coalition discipline:', self.members[member_id]['coalition_discipline']
      except:
        pass
    else:
      try:
        self.members[member_id]['opposition_discipline'] = float(soup.findAll('label')[4].parent.span.text.replace('%',''))
        print 'opposition discipline:', self.members[member_id]['opposition_discipline']
      except:
        pass

    
    try:
      self.members[member_id]['against_own'] = int(soup.findAll('label')[6].parent.span.text)
    except:
      self.members[member_id]['against_own'] = 0
    print 'vote against own:', self.members[member_id]['against_own']

    return data

  def printStats(self, results, category):
    print '  Avgerage:', numpy.average(results)
    
    print '  Median:  ', numpy.median(results)

    minimal = min(results)
    print '  Minimum: ', minimal
    for i, m in self.members.items():
      if category in m and m[category] == minimal:
        print ' '*4, m['data']['name'].encode('utf-8')
    
    maximal = max(results)
    print '  Maxmum:  ', maximal
    for i, m in self.members.items():
      if category in m and m[category] == maximal:
        print ' '*4, m['data']['name'].encode('utf-8')